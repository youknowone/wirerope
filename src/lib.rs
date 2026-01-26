use pyo3::prelude::*;

mod callable;
mod rope;
mod rope_core;
mod wire;

use rope::{CallableFunctionRope, FunctionRope, MethodRope, PropertyRope, WireRope};
use rope_core::RopeCore;
use wire::Wire;

/// A Python module implemented in Rust.
#[pymodule]
fn _wirerope_rust(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Wire>()?;
    m.add_class::<WireRope>()?;
    m.add_class::<RopeCore>()?;
    m.add_class::<MethodRope>()?;
    m.add_class::<PropertyRope>()?;
    m.add_class::<FunctionRope>()?;
    m.add_class::<CallableFunctionRope>()?;

    Ok(())
}
