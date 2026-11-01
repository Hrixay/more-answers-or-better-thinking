"""Prototype puzzle generator for Study 1 (teaching prototype; nothing decided). See README.md."""

from .puzzle import GENERATOR_VERSION, STRUCTURE_LEVELS, Params, Puzzle, generate, render_solution
from .rng import HashRNG, derive_seed
