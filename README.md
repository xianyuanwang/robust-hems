# Robust HEMS - Home Energy Management System

A Python-based Home Energy Management System (HEMS) project featuring algorithm implementations and testing frameworks for residential energy storage optimization.

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Usage](#usage)
- [Testing](#testing)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [License](#license)

## 🎯 Overview

Robust HEMS is a comprehensive home energy management system that provides:

- **Algorithm Implementations**: Core sorting and optimization algorithms for energy scheduling
- **AI-Powered Scheduling**: Advanced algorithms for residential energy storage optimization
- **Testing Framework**: Comprehensive test suites to ensure algorithm correctness
- **Modular Architecture**: Clean, maintainable code structure for easy extension

The system focuses on optimizing household energy costs, maximizing local self-consumption, and maintaining safe battery operations through intelligent scheduling.

## ✨ Features

- **Bubble Sort Algorithm**: Efficient implementation with both functional and in-place sorting options
  - Time Complexity: O(n²) worst/average case, O(n) best case (with early exit optimization)
  - Space Complexity: O(1) for in-place sorting
  - Stable sorting algorithm preserving relative order of equal elements
  
- **Energy Storage AI Scheduling**: Model Predictive Control (MPC) based optimization
  - Cost minimization through peak/valley arbitrage
  - PV generation self-consumption maximization
  - Battery state-of-charge (SOC) management
  - Grid power flow optimization
  
- **Comprehensive Testing**: Unit tests covering edge cases and typical scenarios
  - Empty arrays, single elements, sorted/unsorted inputs
  - Negative numbers and duplicate values
  - Both functional and in-place sorting validation

## 📁 Project Structure

```
robust-hems/
├── src/                    # Source code directory
│   └── bubble_sort.py      # Bubble sort algorithm implementation
├── test/                   # Test directory
│   ├── bubble_sort.py      # Copy of bubble sort for testing
│   └── test.py             # Test suite for bubble sort
├── docs/                   # Documentation
│   └── hems_ai_scheduling_algorithm.md  # Detailed AI scheduling algorithm documentation
└── README.md               # This file
```

### Key Files

- **`src/bubble_sort.py`**: Core bubble sort implementation with two interfaces:
  - `bubble_sort(arr)`: Returns a new sorted list without modifying the original
  - `bubble_sort_inplace(arr)`: Sorts the list in-place and returns the reference

- **`test/test.py`**: Comprehensive test suite validating algorithm correctness across multiple scenarios

- **`docs/hems_ai_scheduling_algorithm.md`**: Detailed technical documentation on HEMS AI scheduling algorithms, including:
  - System architecture and objectives
  - Mathematical formulations and constraints
  - Optimization strategies (LP/MILP, DP, RL)
  - Implementation recommendations

## 🚀 Installation

### Prerequisites

- Python 3.7 or higher
- No external dependencies required for core functionality

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd robust-hems
```

2. (Optional) Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

## 💻 Usage

### Basic Bubble Sort Usage

```python
from src.bubble_sort import bubble_sort, bubble_sort_inplace

# Functional approach - returns new sorted list
original = [5, 3, 8, 1, 9]
sorted_list = bubble_sort(original)
print(f"Original: {original}")    # [5, 3, 8, 1, 9]
print(f"Sorted: {sorted_list}")   # [1, 3, 5, 8, 9]

# In-place approach - modifies original list
data = [4, 2, 7, 1, 6]
bubble_sort_inplace(data)
print(f"Sorted in-place: {data}")  # [1, 2, 4, 6, 7]
```

### Running Tests

Execute the test suite to verify algorithm correctness:

```bash
cd test
python test.py
```

Expected output:
```
Passed 6/6 tests
```

## 🧪 Testing

The test suite covers various scenarios:

| Test Case | Input | Expected Output | Description |
|-----------|-------|-----------------|-------------|
| Empty array | `[]` | `[]` | Edge case: empty input |
| Single element | `[1]` | `[1]` | Edge case: single element |
| Already sorted | `[1, 2, 3, 4]` | `[1, 2, 3, 4]` | Best case scenario |
| Reverse sorted | `[4, 3, 2, 1]` | `[1, 2, 3, 4]` | Worst case scenario |
| Duplicates | `[3, 1, 2, 1]` | `[1, 1, 2, 3]` | Stability verification |
| Negative numbers | `[5, -1, 3, 0]` | `[-1, 0, 3, 5]` | Mixed positive/negative |

Both `bubble_sort` and `bubble_sort_inplace` functions are tested independently to ensure consistency.

## 📚 Documentation

### Algorithm Documentation

For detailed information about the HEMS AI scheduling algorithm, refer to:
- **[HEMS AI Scheduling Algorithm](docs/hems_ai_scheduling_algorithm.md)**: Comprehensive guide covering:
  - System overview and objectives
  - Mathematical modeling and constraints
  - Optimization approaches (MPC, MILP, Dynamic Programming, Reinforcement Learning)
  - Implementation strategies and best practices

### Bubble Sort Algorithm Details

**Algorithm Principle:**
1. Repeatedly traverse the array, comparing adjacent elements
2. Swap elements if they are in the wrong order
3. Each pass moves the largest unsorted element to its correct position
4. Continue until no swaps are needed or n-1 passes completed

**Complexity Analysis:**
- **Time Complexity**: 
  - Worst/Average: O(n²)
  - Best (already sorted): O(n) with early exit optimization
- **Space Complexity**: O(1) for in-place version
- **Stability**: Stable (preserves relative order of equal elements)

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code Standards

- All code comments and documentation must be written in English
- Follow PEP 8 style guidelines for Python code
- Include docstrings for all public functions and classes
- Add unit tests for new features
- Ensure existing tests pass before submitting PR

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🔗 Related Resources

- [Python Official Documentation](https://docs.python.org/)
- [Sorting Algorithms Visualization](https://www.toptal.com/developers/sorting-algorithms)
- [Home Energy Management Systems Research](https://ieeexplore.ieee.org/)

## 📞 Support

For questions, issues, or suggestions, please open an issue in the repository's issue tracker.

---

**Note**: This project is part of a larger Home Energy Management System initiative focused on optimizing residential energy storage and consumption through intelligent algorithms.
