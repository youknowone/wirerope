use pyo3::prelude::*;

/// The base rope object - Rust implementation of RopeCore
#[pyclass(module = "wirerope._wirerope_rust", dict, subclass)]
pub struct RopeCore {
    #[pyo3(get)]
    pub wrapped_object: PyObject,
    #[pyo3(get)]
    pub rope: PyObject,
}

impl Clone for RopeCore {
    fn clone(&self) -> Self {
        Python::with_gil(|py| RopeCore {
            wrapped_object: self.wrapped_object.clone_ref(py),
            rope: self.rope.clone_ref(py),
        })
    }
}

#[pymethods]
impl RopeCore {
    #[new]
    pub fn new(wrapped_object: PyObject, rope: PyObject) -> Self {
        RopeCore {
            wrapped_object,
            rope,
        }
    }

    #[getter]
    fn wire_class(&self, py: Python) -> PyResult<PyObject> {
        self.rope.getattr(py, "wire_class")
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

/// Helper function to copy wrapped attributes
pub fn copy_wrapped_attributes(
    py: Python,
    wrapped_obj: &PyObject,
    target: &PyObject,
) -> PyResult<()> {
    let attrs = vec![
        "__doc__",
        "__name__",
        "__module__",
        "__qualname__",
        "__annotations__",
    ];

    // For hybridmethod/hybridproperty, we need to get attributes from __func__
    let source_obj = if wrapped_obj.getattr(py, "__func__").is_ok() {
        wrapped_obj.getattr(py, "__func__")?
    } else {
        wrapped_obj.clone_ref(py)
    };

    // Copy attributes from source object to target
    for attr in attrs {
        if let Ok(value) = source_obj.getattr(py, attr) {
            if !value.is_none(py) {
                let _ = target.setattr(py, attr, value);
            }
        }
    }

    Ok(())
}
