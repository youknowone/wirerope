use pyo3::prelude::*;
use pyo3::types::{PyDict, PyTuple};
use std::sync::OnceLock;

// Cached type objects for fast pointer comparison
static FUNCTION_TYPE: OnceLock<PyObject> = OnceLock::new();
static CLASSMETHOD_TYPE: OnceLock<PyObject> = OnceLock::new();
static STATICMETHOD_TYPE: OnceLock<PyObject> = OnceLock::new();

/// Initialize type cache for fast type checking
fn ensure_type_cache_initialized(py: Python) -> PyResult<()> {
    // Initialize function type
    if FUNCTION_TYPE.get().is_none() {
        let func_type = py.import("types")?.getattr("FunctionType")?.unbind();
        let _ = FUNCTION_TYPE.set(func_type);
    }

    // Initialize classmethod type
    if CLASSMETHOD_TYPE.get().is_none() {
        let cls_type = py.import("builtins")?.getattr("classmethod")?.unbind();
        let _ = CLASSMETHOD_TYPE.set(cls_type);
    }

    // Initialize staticmethod type
    if STATICMETHOD_TYPE.get().is_none() {
        let static_type = py.import("builtins")?.getattr("staticmethod")?.unbind();
        let _ = STATICMETHOD_TYPE.set(static_type);
    }

    Ok(())
}

/// Fast type checking using cached type objects
fn is_function_type(py: Python, obj: &PyObject) -> PyResult<bool> {
    ensure_type_cache_initialized(py)?;
    let function_type = FUNCTION_TYPE.get().unwrap();
    Ok(obj.bind(py).get_type().is(&function_type.bind(py)))
}

fn is_classmethod_type(py: Python, obj: &PyObject) -> PyResult<bool> {
    ensure_type_cache_initialized(py)?;
    let classmethod_type = CLASSMETHOD_TYPE.get().unwrap();
    Ok(obj.bind(py).get_type().is(&classmethod_type.bind(py)))
}

fn is_staticmethod_type(py: Python, obj: &PyObject) -> PyResult<bool> {
    ensure_type_cache_initialized(py)?;
    let staticmethod_type = STATICMETHOD_TYPE.get().unwrap();
    Ok(obj.bind(py).get_type().is(&staticmethod_type.bind(py)))
}

/// Rust implementation of descriptor_bind logic
/// Returns (owner, binder) tuple like Python version
pub fn descriptor_bind(
    py: Python,
    descriptor: &PyObject,
    obj: &PyObject,
    type_: &PyObject,
) -> PyResult<(PyObject, Option<PyObject>)> {
    // Fast path: use cached type checking (no string comparisons!)
    if is_function_type(py, descriptor)? {
        return Ok((obj.clone_ref(py), Some(obj.clone_ref(py))));
    }

    if is_classmethod_type(py, descriptor)? {
        return Ok((type_.clone_ref(py), Some(type_.clone_ref(py))));
    }

    if is_staticmethod_type(py, descriptor)? {
        return Ok((type_.clone_ref(py), None));
    }

    // For other descriptors, we need to call __get__ and analyze the result
    let method = descriptor.call_method1(py, "__get__", (obj, type_))?;

    // Check if it's a function (not a bound method) - probably staticmethod
    let method_type = method.bind(py).get_type();
    let method_type_name = method_type.name()?;

    if method_type_name == "function" {
        return Ok((type_.clone_ref(py), None));
    }

    // Check if method is obj itself
    if method.bind(py).is(obj.bind(py)) {
        return Ok((obj.clone_ref(py), Some(obj.clone_ref(py))));
    }

    // Check if method is type itself
    if method.bind(py).is(type_.bind(py)) {
        return Ok((type_.clone_ref(py), Some(type_.clone_ref(py))));
    }

    // For bound methods, check __self__ to determine owner
    if method_type_name == "method" {
        if let Ok(self_attr) = method.getattr(py, "__self__") {
            if self_attr.bind(py).is(obj.bind(py)) {
                return Ok((obj.clone_ref(py), Some(obj.clone_ref(py))));
            } else if self_attr.bind(py).is(type_.bind(py)) {
                return Ok((type_.clone_ref(py), Some(type_.clone_ref(py))));
            }
        }
    }

    // Check if method is the descriptor itself (non-method descriptor)
    if method.bind(py).is(descriptor.bind(py)) {
        return Ok((type_.clone_ref(py), None));
    }

    // Default case - return type with no binder
    Ok((type_.clone_ref(py), None))
}

/// The core data object for each function or bound method.
///
/// This is the Rust implementation of the Wire class, providing
/// high-performance method wrapping functionality.
#[pyclass(subclass, dict, module = "wirerope._wirerope_rust")]
pub struct Wire {
    #[pyo3(get, name = "_rope")]
    rope: PyObject,
    #[pyo3(get, name = "_wrapped_object")]
    wrapped_object: PyObject,
    #[pyo3(get, name = "_binding")]
    binding: Option<(PyObject, PyObject)>,
    #[pyo3(get)]
    __func__: PyObject,
    #[pyo3(get, name = "_owner")]
    owner: PyObject,
    #[pyo3(get, name = "_bound_objects")]
    bound_objects: Py<PyTuple>,
    // Store wrapped attributes if rope._wrapped is True
    #[pyo3(get)]
    __doc__: Option<String>,
    #[pyo3(get)]
    __name__: Option<String>,
    #[pyo3(get)]
    __module__: Option<String>,
    // Cache property fget for direct access
    property_fget: Option<PyObject>,
}

#[pymethods]
impl Wire {
    #[new]
    pub fn new(
        rope: PyObject,
        owner: PyObject,
        binding: Option<(PyObject, PyObject)>,
    ) -> PyResult<Self> {
        Python::with_gil(|py| {
            // Get wrapped_object from rope
            let wrapped_object = rope.getattr(py, "wrapped_object")?;

            // Determine __func__ and property_fget based on binding
            let is_property = crate::callable::is_property(py, wrapped_object.clone_ref(py))?;
            let (func, property_fget) = if let Some(ref binding_tuple) = binding {
                if is_property {
                    // For properties, extract the getter function
                    // Try fget first (for regular property), then __func__ (for custom descriptors)
                    let fget = if let Ok(fget_attr) = wrapped_object.getattr(py, "fget") {
                        fget_attr
                    } else if let Ok(func_attr) = wrapped_object.getattr(py, "__func__") {
                        func_attr
                    } else {
                        return Err(pyo3::exceptions::PyAttributeError::new_err(
                            "Property-like descriptor has neither 'fget' nor '__func__' attribute",
                        ));
                    };
                    // Store fget for direct access in _on_property
                    let property_fget = Some(fget.clone_ref(py));

                    // Create a bound method for __func__
                    // This simulates functools.partial behavior
                    let get_method = wrapped_object.getattr(py, "__get__")?;
                    let bound_func = get_method.call1(py, (&binding_tuple.0, &binding_tuple.1))?;
                    (bound_func, property_fget)
                } else {
                    // For methods, call __get__
                    let func = wrapped_object.call_method1(
                        py,
                        "__get__",
                        (&binding_tuple.0, &binding_tuple.1),
                    )?;
                    (func, None)
                }
            } else {
                // For functions without binding
                let obj_type = wrapped_object.bind(py).get_type();
                let type_name = obj_type.name()?;

                // Check if it's a classmethod or staticmethod that needs unwrapping
                // (but NOT a bound method, which also has __func__)
                if (type_name == "classmethod" || type_name == "staticmethod")
                    && wrapped_object.bind(py).hasattr("__func__")?
                {
                    // It's a classmethod or staticmethod, get the underlying function
                    let func = wrapped_object.getattr(py, "__func__")?;
                    (func, None)
                } else {
                    // Regular function or bound method, use wrapped_object directly
                    (wrapped_object.clone_ref(py), None)
                }
            };

            // Calculate bound_objects using Rust descriptor_bind
            let bound_objects = if let Some(ref binding_tuple) = binding {
                // Use Rust implementation of descriptor_bind
                let (_, binder) =
                    descriptor_bind(py, &wrapped_object, &binding_tuple.0, &binding_tuple.1)?;

                // If binder is not None, add it to bound_objects
                if let Some(binder_obj) = binder {
                    PyTuple::new(py, vec![binder_obj])
                } else {
                    Ok(PyTuple::empty(py))
                }
            } else {
                Ok(PyTuple::empty(py))
            }?
            .unbind();

            // Check if rope._wrapped is True
            let wrapped: bool = rope
                .getattr(py, "_wrapped")
                .unwrap_or(py.None())
                .extract(py)
                .unwrap_or(false);

            // Extract attributes if wrapped
            let (__doc__, __name__, __module__) = if wrapped {
                // Try to get attributes from wrapped_object
                let mut doc: Option<String> = None;
                let mut name: Option<String> = None;
                let mut module: Option<String> = None;

                if let Ok(doc_obj) = wrapped_object.getattr(py, "__doc__") {
                    if !doc_obj.is_none(py) {
                        doc = doc_obj.extract(py).ok();
                    }
                }

                if let Ok(name_obj) = wrapped_object.getattr(py, "__name__") {
                    if !name_obj.is_none(py) {
                        name = name_obj.extract(py).ok();
                    }
                }

                if let Ok(module_obj) = wrapped_object.getattr(py, "__module__") {
                    if !module_obj.is_none(py) {
                        module = module_obj.extract(py).ok();
                    }
                }

                (doc, name, module)
            } else {
                (None, None, None)
            };

            // Check if __func__ is callable (like Python's assert callable(self.__func__))
            if !func.bind(py).is_callable() && !is_property {
                let type_name = func
                    .bind(py)
                    .get_type()
                    .name()
                    .map(|n| n.to_string())
                    .unwrap_or_else(|_| "<unknown>".to_string());
                return Err(pyo3::exceptions::PyTypeError::new_err(format!(
                    "Expected callable __func__, got '{}'",
                    type_name
                )));
            }

            let wire = Wire {
                rope,
                wrapped_object,
                binding,
                __func__: func,
                owner,
                bound_objects,
                __doc__,
                __name__,
                __module__,
                property_fget,
            };

            Ok(wire)
        })
    }

    // Note: __call__ is intentionally not implemented to maintain compatibility
    // with Python implementation where Wire objects are not directly callable

    fn _on_property(&self) -> PyResult<PyObject> {
        Python::with_gil(|py| {
            // Optimized property access - use cached property getter when possible
            if let Some(ref binding) = self.binding {
                // Check if we have a cached property getter for direct access
                if let Some(ref property_fget) = self.property_fget {
                    // Direct call to the cached getter with self
                    return property_fget.call1(py, (&binding.0,));
                }

                // Fallback: call __get__ on the wrapped_object (the property descriptor)
                // This is needed for built-in properties that don't have fget
                self.wrapped_object
                    .call_method1(py, "__get__", (&binding.0, &binding.1))
            } else {
                // No binding, call the function directly
                self.__func__.call0(py)
            }
        })
    }
}
