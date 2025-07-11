"""Simulator generation for Assassyn."""

from __future__ import annotations

import os
from ...analysis import topo_downstream_modules, get_upstreams
from .utils import dtype_to_rust_type, int_imm_dumper_impl, fifo_name
from ...builder import SysBuilder
from ...ir.block import CycledBlock
from ...ir.expr import Expr
from ...ir.module import Downstream, Module, SRAM
from ...utils import namify


def dump_simulator( #pylint: disable=too-many-locals, too-many-branches, too-many-statements
                   sys: SysBuilder, config, fd):
    """Generate the simulator module.

    This matches the Rust function in src/backend/simulator/elaborate.rs

    Args:
        sys: The Assassyn system builder
        config: Configuration dictionary with the following keys:
            - idle_threshold: Idle threshold for the simulator
            - sim_threshold: Maximum number of simulation cycles
            - random: Whether to randomize module execution order
            - resource_base: Path to resource files
            - fifo_depth: Default FIFO depth
        fd: File descriptor to write to
    """
    # Write imports
    fd.write("use std::collections::VecDeque;\n")
    fd.write("use super::runtime::*;\n")
    fd.write("use num_bigint::{BigInt, BigUint};\n")
    fd.write("use rand::seq::SliceRandom;\n\n")

    # Initialize data structures
    simulator_init = []
    downstream_reset = []
    registers = []

    # Begin simulator struct definition
    fd.write("pub struct Simulator { pub stamp: usize, ")

    # Add array fields to simulator struct
    for elem in sys.arrays:

        for array in elem.partition:
            name = namify(array.name)

            dtype = dtype_to_rust_type(array.scalar_ty)
            fd.write(f"pub {name} : Array<{dtype}>, ")

            # Handle array initialization
            if array.initializer:
                init_values = []
                for x in array.initializer:
                    init_values.append(int_imm_dumper_impl(array.scalar_ty, x))
                init_str = ", ".join(init_values)
                simulator_init.append(f"{name} : Array::new_with_init(vec![{init_str}]),")
            else:
                simulator_init.append(f"{name} : Array::new({array.size}),")

            registers.append(name)

    # Track expressions with external visibility
    expr_validities = set()

    # Add module fields to simulator struct
    for module in sys.modules[:] + sys.downstreams[:]:
        module_name = namify(module.name)

        # Add triggered flag for all modules
        fd.write(f"pub {module_name}_triggered : bool, ")
        simulator_init.append(f"{module_name}_triggered : false,")
        downstream_reset.append(f"self.{module_name}_triggered = false;")

        if isinstance(module, Module):
            # Add event queue for non-downstream modules
            fd.write(f"pub {module_name}_event : VecDeque<usize>, ")
            simulator_init.append(f"{module_name}_event : VecDeque::new(),")

            # Add FIFO fields for each FIFO
            for fifo in module.ports:
                name = fifo_name(fifo)
                ty = dtype_to_rust_type(fifo.dtype)
                fd.write(f"pub {name} : FIFO<{ty}>, ")
                simulator_init.append(f"{name} : FIFO::new(),")
                registers.append(name)
        elif isinstance(module, Downstream):
            # Gather expressions with external visibility for downstream modules
            for expr in module.externals:
                if isinstance(expr, Expr):
                    expr_validities.add(expr)

    # Add value validity tracking for expressions with external visibility
    for expr in expr_validities:
        name = namify(expr.as_operand())
        dtype = dtype_to_rust_type(expr.dtype)
        fd.write(f"pub {name}_value : Option<{dtype}>, ")
        simulator_init.append(f"{name}_value : None,")
        downstream_reset.append(f"self.{name}_value = None;")

    # Close simulator struct
    fd.write("}\n\n")

    # Begin simulator implementation
    fd.write("impl Simulator {\n")

    # Constructor
    fd.write("  pub fn new() -> Self {\n")
    fd.write("    Simulator {\n")
    fd.write("      stamp: 0,\n")
    for init in simulator_init:
        fd.write(f"      {init}\n")
    fd.write("    }\n")
    fd.write("  }\n\n")

    # Event validity check
    fd.write("  fn event_valid(&self, event: &VecDeque<usize>) -> bool {\n")
    fd.write("    event.front().map_or(false, |x| *x <= self.stamp)\n")
    fd.write("  }\n\n")

    # Reset downstream method
    fd.write("  pub fn reset_downstream(&mut self) {\n")
    for reset in downstream_reset:
        fd.write(f"    {reset}\n")
    fd.write("  }\n\n")

    # Tick registers method
    fd.write("  pub fn tick_registers(&mut self) {\n")
    for reg in registers:
        fd.write(f"    self.{reg}.tick(self.stamp);\n")
    fd.write("  }\n\n")

    # Critical path analysis
    # TODO(@derui): Implement critical path analysis equivalent to Rust

    # Get topological order for downstream modules
    downstreams = topo_downstream_modules(sys)

    # Module simulation functions
    simulators = []
    for module in sys.modules[:] + sys.downstreams[:]:
        module_name = namify(module.name)
        fd.write(f"  fn simulate_{module_name}(&mut self) {{\n")

        if not isinstance(module, Downstream):
            # Event based triggering for non-downstream modules
            fd.write(f"    if self.event_valid(&self.{module_name}_event) {{\n")
        else:
            # Dependency based triggering for downstream modules
            upstream_conds = []
            print(f"Module {module_name} upstreams:")
            for upstream in get_upstreams(module):
                print(f"  {upstream.name}")
                upstream_name = namify(upstream.name)
                upstream_conds.append(f"self.{upstream_name}_triggered")

            conds = " || ".join(upstream_conds) if upstream_conds else "false"
            fd.write(f"    if {conds} {{\n")

        # Call module function and handle result
        fd.write(f"      let succ = super::modules::{module_name}(self);\n")

        if not isinstance(module, Downstream):
            # Pop event on success
            fd.write(f"      if succ {{ self.{module_name}_event.pop_front(); }}\n")
            fd.write("      else {\n")

            # Reset externally used values on failure
            for expr in expr_validities:
                if expr.parent.module == module:
                    name = namify(expr.as_operand())
                    fd.write(f"        self.{name}_value = None;\n")

            fd.write("      }\n")
            simulators.append(module_name)

        # Update trigger state and close condition
        fd.write(f"      self.{module_name}_triggered = succ;\n")
        fd.write("    } // close event condition\n")
        fd.write("  } // close function\n\n")

    # Close simulator impl
    fd.write("}\n\n")

    # Generate simulate function
    fd.write("pub fn simulate() {\n")
    fd.write("  let mut sim = Simulator::new();\n")

    # Handle randomization if enabled
    if config.get('random', False):
        fd.write("  let mut rng = rand::thread_rng();\n")
        fd.write("  let mut simulators : Vec<fn(&mut Simulator)> = vec![")
    else:
        fd.write("  let simulators : Vec<fn(&mut Simulator)> = vec![")

    # Add simulators for all non-downstream modules
    for sim in simulators:
        fd.write(f"Simulator::simulate_{sim}, ")
    fd.write("];\n")

    # Add simulators for downstream modules
    fd.write("  let downstreams : Vec<fn(&mut Simulator)> = vec![")
    for downstream in downstreams:
        module_name = downstream.name
        fd.write(f"Simulator::simulate_{module_name}, ")
    fd.write("];\n")

    # Initialize memory from files if needed
    for sram in [m for m in sys.modules if isinstance(m, SRAM)]:
        init_file_path = os.path.join(config.get('resource_base', '.'), sram.init_file)
        array = sram.payload
        array_name = namify(array.name)
        fd.write(f'  load_hex_file(&mut sim.{array_name}.payload, "{init_file_path}");\n')

    # Set simulation threshold and other parameters
    sim_threshold = config.get('sim_threshold', 100)

    # Add initial events for driver if present
    if sys.has_module("Driver") is not None:
        fd.write(f"""
        for i in 1..={sim_threshold} {{ sim.Driver_event.push_back(i * 100); }} """)

    # Add initial events for testbench if present
    testbench = sys.has_module("Testbench")
    if testbench is not None:
        cycles = []

        # Collect cycles from testbench blocks
        for block in testbench.body.body:
            if isinstance(block, CycledBlock):
                cycles.append(block.cycle)

        if cycles:
            fd.write(f"""
              let tb_cycles = vec![{', '.join(map(str, cycles))}];
              for cycle in tb_cycles {{
                sim.Testbench_event.push_back(cycle * 100);
              }}
            """)

    # Generate main simulation loop
    randomization = ""
    if config.get('random', False):
        randomization = "    simulators.shuffle(&mut rng);\n"

    # Get idle threshold parameter
    idle_threshold = config.get('idle_threshold', 5)

    # Add idle threshold check
    any_module_triggered = 'let any_module_triggered =' + \
                           ' || '.join([f"sim.{namify(m.name)}_triggered" for m in sys.modules])

    fd.write(f"""
      let mut idle_count = 0;
      for i in 1..={sim_threshold} {{
        sim.stamp = i * 100;
        sim.reset_downstream();
{randomization}
        for simulate in simulators.iter() {{
          simulate(&mut sim);
        }}

        for simulate in downstreams.iter() {{
          simulate(&mut sim);
        }}

        {any_module_triggered};

        // Handle idle threshold
        if !any_module_triggered {{
          idle_count += 1;
          if idle_count >= {idle_threshold} {{
            println!("Simulation stopped due to reaching idle threshold of {idle_threshold}");
            break;
          }}
        }} else {{
          idle_count = 0;
        }}

        sim.stamp += 50;
        sim.tick_registers();
      }}
    """)

    # Close simulate function
    fd.write("}\n")

    return True


def dump_main(fd):
    """Generate the main.rs file.

    This matches the Rust function in src/backend/simulator/elaborate.rs
    """
    fd.write("""
mod runtime;
mod modules;
mod simulator;

fn main() {
  simulator::simulate();
}
    """)
    return True
