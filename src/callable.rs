use pyo3::prelude::*;
use std::sync::OnceLock;

// Cached type objects for fast type checking
static FUNCTION_TYPE: OnceLock<PyObject> = OnceLock::new();
static METHOD_TYPE: OnceLock<PyObject> = OnceLock::new();
static PROPERTY_TYPE: OnceLock<PyObject> = OnceLock::new();

/// Initialize type cache for fast type checking
fn ensure_type_cache_initialized(py: Python) -> PyResult<()> {
    if FUNCTION_TYPE.get().is_none() {
        let func_type = py.import("types")?.getattr("FunctionType")?.unbind();
        let _ = FUNCTION_TYPE.set(func_type);
    }

    if METHOD_TYPE.get().is_none() {
        let method_type = py.import("types")?.getattr("MethodType")?.unbind();
        let _ = METHOD_TYPE.set(method_type);
    }

    if PROPERTY_TYPE.get().is_none() {
        let property_type = py.import("builtins")?.getattr("property")?.unbind();
        let _ = PROPERTY_TYPE.set(property_type);
    }

    Ok(())
}

/// Check if a callable is a bare function (not a method)
#[pyfunction]
pub fn is_barefunction(py: Python, func: PyObject) -> PyResult<bool> {
    ensure_type_cache_initialized(py)?;
    let function_type = FUNCTION_TYPE.get().unwrap();

    if func.bind(py).get_type().is(&function_type.bind(py)) {
        // Check qualname == name to detect bare functions
        if let (Ok(qualname), Ok(name)) = (
            func.getattr(py, "__qualname__"),
            func.getattr(py, "__name__"),
        ) {
            let qualname_str: String = qualname.extract(py)?;
            let name_str: String = name.extract(py)?;

            // Python's logic: split by "<locals>." and take the last part
            let method_name = qualname_str
                .split("<locals>.")
                .last()
                .unwrap_or(&qualname_str);
            return Ok(method_name == name_str);
        }
    }
    Ok(false)
}

/// Check if a callable is a bound method
#[pyfunction]
pub fn is_boundmethod(py: Python, func: PyObject) -> PyResult<bool> {
    ensure_type_cache_initialized(py)?;
    let method_type = METHOD_TYPE.get().unwrap();
    Ok(func.bind(py).get_type().is(&method_type.bind(py)))
}

/// Check if a callable is a property descriptor
#[pyfunction]
pub fn is_property(py: Python, func: PyObject) -> PyResult<bool> {
    ensure_type_cache_initialized(py)?;
    let property_type = PROPERTY_TYPE.get().unwrap();

    // Check if it's a builtin property
    if func.bind(py).get_type().is(&property_type.bind(py)) {
        return Ok(true);
    }

    // Check if it has property-like behavior (has __get__ and class name contains 'property')
    if func.bind(py).hasattr("__get__")? {
        if let Ok(class_name) = func.bind(py).get_type().name() {
            if class_name.to_string().contains("property") {
                return Ok(true);
            }
        }
    }

    Ok(false)
}

/// Get the wrapped object (always returns the input)
#[pyfunction]
pub fn get_wrapped_object(_py: Python, func: PyObject) -> PyResult<PyObject> {
    Ok(func)
}

/// Extract the wrapped callable from a descriptor
#[pyfunction]
pub fn get_wrapped_callable(py: Python, func: PyObject) -> PyResult<PyObject> {
    // For descriptors, try to extract the actual function
    if let Ok(func_attr) = func.getattr(py, "__func__") {
        return Ok(func_attr);
    }

    if let Ok(fget_attr) = func.getattr(py, "fget") {
        if !fget_attr.is_none(py) {
            return Ok(fget_attr);
        }
    }

    // Default: return the object itself
    Ok(func)
}
