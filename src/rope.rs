use crate::callable::{get_wrapped_callable, is_barefunction, is_boundmethod, is_property};
use crate::rope_core::{copy_wrapped_attributes, RopeCore};
use crate::wire::descriptor_bind;
use parking_lot::Mutex;
use pyo3::exceptions::PyAssertionError;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyTuple};
use pyo3::PyTypeInfo;
use std::collections::HashMap;
use std::sync::OnceLock;

/// The main wrapper interface for callables.
///
/// This is the Rust implementation of WireRope, providing high-performance
/// dispatching for different callable types.
#[pyclass(module = "wirerope._wirerope_rust", dict)]
pub struct WireRope {
    #[pyo3(get)]
    wire_class: PyObject,
    method_rope: PyObject,
    property_rope: PyObject,
    function_rope: PyObject,
    callable_function_rope: PyObject,
    #[pyo3(get, name = "_wrapped")]
    wrapped: bool,
    #[pyo3(get, name = "_args")]
    args: Option<PyObject>,
}

#[pymethods]
impl WireRope {
    #[new]
    #[pyo3(signature = (wire_class, core_class=None, wraps=false, rope_args=None))]
    pub fn new(
        py: Python,
        wire_class: PyObject,
        core_class: Option<PyObject>,
        wraps: bool,
        rope_args: Option<PyObject>,
    ) -> PyResult<Self> {
        // Get RopeCore if not provided
        let _core_class = match core_class {
            Some(c) => c,
            None => RopeCore::type_object(py).into(),
        };

        // Create rope type classes dynamically

        // Create the rope classes using Rust implementations
        let method_rope = MethodRope::type_object(py);
        let property_rope = PropertyRope::type_object(py);
        let function_rope = FunctionRope::type_object(py);
        let callable_function_rope = CallableFunctionRope::type_object(py);

        // Set _wrapped and _args on all rope types
        for rope in &[
            &method_rope,
            &property_rope,
            &function_rope,
            &callable_function_rope,
        ] {
            rope.setattr("_wrapped", wraps)?;
            rope.setattr("_args", &rope_args)?;
        }

        Ok(WireRope {
            wire_class,
            method_rope: method_rope.into(),
            property_rope: property_rope.into(),
            function_rope: function_rope.into(),
            callable_function_rope: callable_function_rope.into(),
            wrapped: wraps,
            args: rope_args,
        })
    }

    fn __call__(slf: &Bound<'_, Self>, py: Python, func: PyObject) -> PyResult<PyObject> {
        // Use utility functions instead of creating Callable object
        let func_is_barefunction = is_barefunction(py, func.clone_ref(py))?;
        let func_is_boundmethod = is_boundmethod(py, func.clone_ref(py))?;
        let func_is_property = is_property(py, func.clone_ref(py))?;

        // No longer need Callable - pass wrapped_object directly

        let self_ref = slf.borrow();

        // Determine rope class based on callable type
        let rope_class = if func_is_barefunction || func_is_boundmethod {
            // Check if wire_class has custom __call__
            let wire_class_call = self_ref.wire_class.getattr(py, "__call__")?;

            // Try to get __qualname__ to check if it's type.__call__
            let is_default_call = if let Ok(qualname) = wire_class_call.getattr(py, "__qualname__")
            {
                let qualname_str: String = qualname.extract(py).unwrap_or_default();
                qualname_str == "type.__call__"
            } else {
                false
            };

            if is_default_call {
                &self_ref.function_rope
            } else {
                &self_ref.callable_function_rope
            }
        } else if func_is_property {
            &self_ref.property_rope
        } else {
            &self_ref.method_rope
        };

        // Create rope instance
        let kwargs = PyDict::new(py);
        kwargs.set_item("rope", slf)?;
        let rope = rope_class.call(py, (func.clone_ref(py),), Some(&kwargs))?;

        // For CallableFunctionRope, always apply functools.wraps to preserve attributes
        if rope_class
            .bind(py)
            .is(self_ref.callable_function_rope.bind(py))
        {
            let functools = py.import("functools")?;
            let wraps = functools.getattr("wraps")?;
            let wrapped_callable = get_wrapped_callable(py, func.clone_ref(py))?;
            let wrapper = wraps.call1((wrapped_callable,))?;
            Ok(wrapper.call1((rope,))?.into())
        } else if self_ref.wrapped {
            // For other rope types, only apply functools.wraps if _wrapped is True
            let functools = py.import("functools")?;
            let wraps = functools.getattr("wraps")?;
            let wrapped_callable = get_wrapped_callable(py, func.clone_ref(py))?;
            let wrapper = wraps.call1((wrapped_callable,))?;
            Ok(wrapper.call1((rope,))?.into())
        } else {
            Ok(rope)
        }
    }

    fn __setattr__(slf: &Bound<Self>, name: &str, value: PyObject) -> PyResult<()> {
        // Allow setting attributes on the instance
        // This is needed for functools.wraps to work properly
        if let Ok(dict) = slf.getattr("__dict__") {
            dict.set_item(name, value)?;
        }
        Ok(())
    }

    fn __getattr__(slf: &Bound<Self>, name: &str) -> PyResult<PyObject> {
        // First check instance dict
        if let Ok(dict) = slf.getattr("__dict__") {
            if let Ok(value) = dict.get_item(name) {
                if !value.is_none() {
                    return Ok(value.unbind());
                }
            }
        }

        // Fallback to default behavior
        let class_name = slf.get_type().name()?;
        Err(pyo3::exceptions::PyAttributeError::new_err(format!(
            "'{}' object has no attribute '{}'",
            class_name, name
        )))
    }
}

/// MethodRope implementation combining mixin functionality with RopeCore
#[pyclass(module = "wirerope._wirerope_rust", extends=RopeCore, dict)]
pub struct MethodRope {
    #[pyo3(get, set)]
    wire_name: Option<String>,
    #[pyo3(get, name = "_wrapped")]
    wrapped: bool,
    // Cached attributes for performance
    cached_wrapped_object: OnceLock<PyObject>,
    cached_wrapped_callable_name: OnceLock<String>,
    cached_wire_class: OnceLock<PyObject>,
    // Wire cache: (object_id, type_id) -> wire
    wire_cache: Mutex<HashMap<(usize, usize), PyObject>>,
}

#[pymethods]
impl MethodRope {
    #[new]
    #[pyo3(signature = (wrapped_object, *, rope))]
    pub fn new(wrapped_object: PyObject, rope: PyObject) -> PyResult<(Self, RopeCore)> {
        Python::with_gil(|py| {
            // Check if it's a barefunction using utility function
            let is_barefunction =
                crate::callable::is_barefunction(py, wrapped_object.clone_ref(py))?;
            if is_barefunction {
                return Err(PyAssertionError::new_err("Expected not barefunction"));
            }

            let wrapped = rope.getattr(py, "_wrapped")?.extract::<bool>(py)?;

            Ok((
                MethodRope {
                    wire_name: None,
                    wrapped,
                    cached_wrapped_object: OnceLock::new(),
                    cached_wrapped_callable_name: OnceLock::new(),
                    cached_wire_class: OnceLock::new(),
                    wire_cache: Mutex::new(HashMap::new()),
                },
                RopeCore {
                    wrapped_object,
                    rope,
                },
            ))
        })
    }

    fn __set_name__(&mut self, owner: &Bound<'_, PyAny>, name: &str) -> PyResult<()> {
        let owner_name = owner.getattr("__name__")?.extract::<String>()?;
        self.wire_name = Some(format!("__wire|{}|{}", owner_name, name));
        Ok(())
    }

    fn __setattr__(slf: &Bound<Self>, name: &str, value: PyObject) -> PyResult<()> {
        // Allow setting attributes on the instance
        // This is needed for functools.wraps to work properly
        if let Ok(dict) = slf.getattr("__dict__") {
            dict.set_item(name, value)?;
        }
        Ok(())
    }

    fn __getattr__(slf: &Bound<Self>, name: &str) -> PyResult<PyObject> {
        // First check instance dict
        if let Ok(dict) = slf.getattr("__dict__") {
            if let Ok(value) = dict.get_item(name) {
                if !value.is_none() {
                    return Ok(value.unbind());
                }
            }
        }

        // Fallback to default behavior
        let class_name = slf.get_type().name()?;
        Err(pyo3::exceptions::PyAttributeError::new_err(format!(
            "'{}' object has no attribute '{}'",
            class_name, name
        )))
    }

    fn __get__(
        slf: PyRef<Self>,
        obj: &Bound<'_, PyAny>,
        type_: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<PyObject> {
        let py = obj.py();
        let base: &RopeCore = slf.as_ref();

        // Fast path: Check Rust-side cache first
        // Optimize key generation - avoid tuple allocation for common case
        let obj_ptr = obj.as_ptr() as usize;
        let type_ptr = type_.map_or(0, |t| t.as_ptr() as usize);
        let wire_key = (obj_ptr, type_ptr);

        // Try to get from cache
        let cache = slf.wire_cache.lock();
        if let Some(wire) = cache.get(&wire_key) {
            // Wire found in Rust cache, return directly
            return Ok(wire.clone_ref(py));
        }
        drop(cache); // Explicitly drop the lock

        // Slow path: wire not cached, need to create it
        // Get wrapped_object directly from RopeCore
        let co = slf.cached_wrapped_object.get_or_init(|| {
            // Now we have wrapped_object directly in RopeCore
            base.wrapped_object.clone_ref(py)
        });

        // Use descriptor_bind function
        let obj_py = obj.clone().unbind();
        let type_py = type_
            .map(|t| t.clone().unbind())
            .unwrap_or_else(|| py.None());
        let (owner, _) = descriptor_bind(py, co, &obj_py, &type_py)?;

        let owner = if owner.is_none(py) {
            if !obj.is_none() {
                obj.clone().unbind()
            } else if let Some(t) = type_ {
                t.clone().unbind()
            } else {
                obj.clone().unbind()
            }
        } else {
            owner
        };

        let wire_name = if let Some(ref name) = slf.wire_name {
            name.clone()
        } else {
            // Use cached wrapped_callable name
            let func_name = slf.cached_wrapped_callable_name.get_or_init(|| {
                let wrapped_callable =
                    crate::callable::get_wrapped_callable(py, base.wrapped_object.clone_ref(py))
                        .unwrap();
                let name: String = wrapped_callable
                    .getattr(py, "__name__")
                    .unwrap()
                    .extract(py)
                    .unwrap();
                name
            });

            let mut wire_name_str = format!("__wire_{}", func_name);
            if let Some(t) = type_ {
                if owner.bind(py).is(t) {
                    let type_name: String = t.getattr("__name__")?.extract()?;
                    wire_name_str.push('_');
                    wire_name_str.push_str(&type_name);
                }
            }
            wire_name_str
        };

        // Try to find existing wire one more time (for dynamically named wires)
        let wire = if slf.wire_name.is_none() {
            owner
                .getattr(py, wire_name.as_str())
                .unwrap_or_else(|_| py.None())
        } else {
            py.None()
        };

        let wire = if wire.is_none(py) {
            // Use cached wire_class
            let wire_class = slf
                .cached_wire_class
                .get_or_init(|| base.rope.getattr(py, "wire_class").unwrap());

            let binding = (
                obj.clone().unbind(),
                type_
                    .map(|t| t.clone().unbind())
                    .unwrap_or_else(|| py.None()),
            );
            let base_py: PyObject = Py::new(py, base.clone())?.into_any();
            let new_wire = wire_class.call1(py, (base_py, &owner, binding))?;

            if slf.wrapped {
                copy_wrapped_attributes(py, co, &new_wire)?;
            }

            owner.setattr(py, wire_name.as_str(), &new_wire)?;

            // Store in Rust cache
            {
                let mut cache = slf.wire_cache.lock();
                cache.insert(wire_key, new_wire.clone_ref(py));
            }

            new_wire
        } else {
            wire
        };

        Ok(wire)
    }
}

/// PropertyRope implementation
#[pyclass(module = "wirerope._wirerope_rust", dict, extends=RopeCore)]
pub struct PropertyRope {
    #[pyo3(get, set)]
    wire_name: Option<String>,
    #[pyo3(get, name = "_wrapped")]
    wrapped: bool,
    // Cached attributes for performance
    cached_wrapped_object: OnceLock<PyObject>,
    cached_wire_class: OnceLock<PyObject>,
    cached_property_fget: OnceLock<Option<PyObject>>,
    // Wire cache: (object_id, type_id) -> wire
    wire_cache: Mutex<HashMap<(usize, usize), PyObject>>,
}

#[pymethods]
impl PropertyRope {
    #[new]
    #[pyo3(signature = (wrapped_object, *, rope))]
    pub fn new(wrapped_object: PyObject, rope: PyObject) -> PyResult<(Self, RopeCore)> {
        Python::with_gil(|py| {
            // Check if it's a barefunction using utility function
            let is_barefunction =
                crate::callable::is_barefunction(py, wrapped_object.clone_ref(py))?;
            if is_barefunction {
                return Err(PyAssertionError::new_err("Expected not barefunction"));
            }

            let wrapped = rope.getattr(py, "_wrapped")?.extract::<bool>(py)?;

            Ok((
                PropertyRope {
                    wire_name: None,
                    wrapped,
                    cached_wrapped_object: OnceLock::new(),
                    cached_wire_class: OnceLock::new(),
                    cached_property_fget: OnceLock::new(),
                    wire_cache: Mutex::new(HashMap::new()),
                },
                RopeCore {
                    wrapped_object,
                    rope,
                },
            ))
        })
    }

    fn __set_name__(&mut self, owner: &Bound<'_, PyAny>, name: &str) -> PyResult<()> {
        let owner_name = owner.getattr("__name__")?.extract::<String>()?;
        self.wire_name = Some(format!("__wire|{}|{}", owner_name, name));
        Ok(())
    }

    fn __get__(
        slf: PyRef<Self>,
        obj: &Bound<'_, PyAny>,
        type_: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<PyObject> {
        let py = obj.py();
        let base: &RopeCore = slf.as_ref();

        // Special handling for class access (obj is None)
        if obj.is_none() {
            // Check if it's a hybridproperty (executes immediately for class access)
            // vs regular property (returns property object for class access)
            let co = slf
                .cached_wrapped_object
                .get_or_init(|| base.wrapped_object.clone_ref(py));

            // Check if it might be a hybridproperty-like descriptor
            if let Ok(class_name) = co.bind(py).get_type().name() {
                if class_name.to_string().contains("property") && class_name != "property" {
                    // It's likely a hybridproperty, call __get__ to get the result
                    if let Some(t) = type_ {
                        return co.call_method1(py, "__get__", (py.None(), t));
                    }
                }
            }

            // For regular properties, return the property object itself
            return Ok(co.clone_ref(py));
        }

        // Fast path: try to get cached property getter and call it directly
        let property_fget = slf.cached_property_fget.get_or_init(|| {
            let wrapped_object = base.wrapped_object.clone_ref(py);

            // First try fget (standard property), then __func__ (custom descriptors)
            if let Ok(fget) = wrapped_object.getattr(py, "fget") {
                Some(fget)
            } else if let Ok(func) = wrapped_object.getattr(py, "__func__") {
                Some(func)
            } else {
                None
            }
        });

        // If we have a direct property getter, use it for maximum performance
        if let Some(ref fget) = property_fget {
            return fget.call1(py, (obj,));
        }

        // Fallback to full Wire creation for complex properties
        let obj_ptr = obj.as_ptr() as usize;
        let type_ptr = type_.map_or(0, |t| t.as_ptr() as usize);
        let wire_key = (obj_ptr, type_ptr);

        // Try to get from cache
        let cache = slf.wire_cache.lock();
        if let Some(wire) = cache.get(&wire_key) {
            let wire_obj = wire.clone_ref(py);
            drop(cache);
            return wire_obj
                .bind(py)
                .call_method0("_on_property")
                .map(|r| r.unbind());
        }
        drop(cache);

        // Slow path: wire not cached, need to create it
        let co = slf
            .cached_wrapped_object
            .get_or_init(|| base.wrapped_object.clone_ref(py));

        let obj_py = obj.clone().unbind();
        let type_py = type_
            .map(|t| t.clone().unbind())
            .unwrap_or_else(|| py.None());
        let (owner, _) = descriptor_bind(py, co, &obj_py, &type_py)?;

        let owner = if owner.is_none(py) {
            obj.clone().unbind()
        } else {
            owner
        };

        let wire_name = if let Some(ref name) = slf.wire_name {
            name.clone()
        } else {
            let wrapped_callable =
                crate::callable::get_wrapped_callable(py, base.wrapped_object.clone_ref(py))?;
            let func_name: String = wrapped_callable.getattr(py, "__name__")?.extract(py)?;
            format!("__wire_{}", func_name)
        };

        // Create new wire
        let wire_class = slf
            .cached_wire_class
            .get_or_init(|| base.rope.getattr(py, "wire_class").unwrap());

        let binding = (
            obj.clone().unbind(),
            type_
                .map(|t| t.clone().unbind())
                .unwrap_or_else(|| py.None()),
        );
        let base_py: PyObject = Py::new(py, base.clone())?.into_any();
        let new_wire = wire_class.call1(py, (base_py, &owner, binding))?;

        if slf.wrapped {
            copy_wrapped_attributes(py, co, &new_wire)?;
        }

        owner.setattr(py, wire_name.as_str(), &new_wire)?;

        // Store in Rust cache
        {
            let mut cache = slf.wire_cache.lock();
            cache.insert(wire_key, new_wire.clone_ref(py));
        }

        new_wire
            .bind(py)
            .call_method0("_on_property")
            .map(|r| r.unbind())
    }

    fn __setattr__(slf: &Bound<Self>, name: &str, value: PyObject) -> PyResult<()> {
        // Allow setting attributes on the instance
        // This is needed for functools.wraps to work properly
        if let Ok(dict) = slf.getattr("__dict__") {
            dict.set_item(name, value)?;
        }
        Ok(())
    }

    fn __getattr__(slf: &Bound<Self>, name: &str) -> PyResult<PyObject> {
        // First check instance dict
        if let Ok(dict) = slf.getattr("__dict__") {
            if let Ok(value) = dict.get_item(name) {
                if !value.is_none() {
                    return Ok(value.unbind());
                }
            }
        }

        // Fallback to default behavior
        let class_name = slf.get_type().name()?;
        Err(pyo3::exceptions::PyAttributeError::new_err(format!(
            "'{}' object has no attribute '{}'",
            class_name, name
        )))
    }
}

#[pyclass(module = "wirerope._wirerope_rust", dict, extends=RopeCore)]
pub struct FunctionRope {
    #[pyo3(get, name = "_wire")]
    wire: PyObject,
    #[pyo3(get, name = "_wrapped")]
    wrapped: bool,
}

#[pymethods]
impl FunctionRope {
    #[new]
    #[pyo3(signature = (wrapped_object, *, rope))]
    pub fn new(wrapped_object: PyObject, rope: PyObject) -> PyResult<(Self, RopeCore)> {
        Python::with_gil(|py| {
            let is_barefunction =
                crate::callable::is_barefunction(py, wrapped_object.clone_ref(py))?;
            let is_boundmethod = crate::callable::is_boundmethod(py, wrapped_object.clone_ref(py))?;
            if !is_barefunction && !is_boundmethod {
                return Err(PyAssertionError::new_err(
                    "Expected barefunction or boundmethod",
                ));
            }

            let wrapped = rope.getattr(py, "_wrapped")?.extract::<bool>(py)?;
            let wire_class = rope.getattr(py, "wire_class")?;
            let base_core = RopeCore {
                wrapped_object: wrapped_object.clone_ref(py),
                rope: rope.clone_ref(py),
            };
            let base_py: PyObject = Py::new(py, base_core.clone())?.into_any();
            let wire = wire_class.call1(py, (base_py, py.None(), py.None()))?;

            if wrapped {
                let wrapped_obj = wrapped_object.clone_ref(py);
                copy_wrapped_attributes(py, &wrapped_obj, &wire)?;
            }

            Ok((FunctionRope { wire, wrapped }, base_core))
        })
    }

    fn __getattr__(slf: &Bound<Self>, name: &str) -> PyResult<PyObject> {
        let py = slf.py();
        // First check instance dict
        if let Ok(dict) = slf.getattr("__dict__") {
            if let Ok(value) = dict.get_item(name) {
                if !value.is_none() {
                    return Ok(value.unbind());
                }
            }
        }

        // For all other attributes, delegate to wire
        let wire = slf.borrow().wire.clone_ref(py);
        wire.getattr(py, name)
    }

    fn __setattr__(slf: &Bound<Self>, name: &str, value: PyObject) -> PyResult<()> {
        // Allow setting attributes on the instance
        // This is needed for functools.wraps to work properly
        if let Ok(dict) = slf.getattr("__dict__") {
            dict.set_item(name, value)?;
        }
        Ok(())
    }
}

#[pyclass(module = "wirerope._wirerope_rust", dict, extends=RopeCore)]
pub struct CallableFunctionRope {
    #[pyo3(get, name = "_wire")]
    wire: PyObject,
    #[pyo3(get, name = "_wrapped")]
    wrapped: bool,
}

#[pymethods]
impl CallableFunctionRope {
    #[new]
    #[pyo3(signature = (wrapped_object, *, rope))]
    pub fn new(wrapped_object: PyObject, rope: PyObject) -> PyResult<(Self, RopeCore)> {
        Python::with_gil(|py| {
            let is_barefunction =
                crate::callable::is_barefunction(py, wrapped_object.clone_ref(py))?;
            let is_boundmethod = crate::callable::is_boundmethod(py, wrapped_object.clone_ref(py))?;
            if !is_barefunction && !is_boundmethod {
                return Err(PyAssertionError::new_err(
                    "Expected barefunction or boundmethod",
                ));
            }

            let wrapped = rope.getattr(py, "_wrapped")?.extract::<bool>(py)?;
            let wire_class = rope.getattr(py, "wire_class")?;
            let base_core = RopeCore {
                wrapped_object: wrapped_object.clone_ref(py),
                rope: rope.clone_ref(py),
            };
            let base_py: PyObject = Py::new(py, base_core.clone())?.into_any();
            let wire = wire_class.call1(py, (base_py, py.None(), py.None()))?;

            if wrapped {
                let wrapped_obj = wrapped_object.clone_ref(py);
                copy_wrapped_attributes(py, &wrapped_obj, &wire)?;
            }

            Ok((CallableFunctionRope { wire, wrapped }, base_core))
        })
    }

    fn __getattr__(slf: PyRef<Self>, py: Python, name: &str) -> PyResult<PyObject> {
        // For all attributes, delegate to wire
        slf.wire.getattr(py, name)
    }

    #[pyo3(signature = (*args, **kwargs))]
    fn __call__(
        slf: PyRef<Self>,
        args: &Bound<'_, PyTuple>,
        kwargs: Option<&Bound<'_, PyDict>>,
    ) -> PyResult<PyObject> {
        let py = slf.py();
        slf.wire.call(py, args, kwargs)
    }
}
