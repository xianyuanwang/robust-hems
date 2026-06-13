"""
Bubble Sort Implementation and Description

Algorithm Principle:
1. Bubble sort repeatedly traverses the array to be sorted, comparing adjacent elements and swapping them if they are in the wrong order;
2. Each pass moves the largest (or smallest) element of the current unsorted portion to one end of that portion, similar to bubbles rising or sinking, hence the name "bubble";
3. Repeat the process until no swaps are needed or the number of passes reaches n-1 (where n is the array length).

Time Complexity:
- Worst/Average: O(n^2)
- Best (already sorted): O(n) (if early exit optimization is implemented)

Space Complexity: O(1) (in-place sorting)

Stability: Stable (relative order of equal elements is preserved)

This file provides two interfaces: `bubble_sort` returns a new list, `bubble_sort_inplace` sorts in-place and returns the original list reference.
"""

from typing import List, Sequence


def bubble_sort(arr: Sequence) -> List:
    """Return a new sorted list (without modifying the original input).

    Example:
    >>> bubble_sort([3,1,2])
    [1,2,3]
    """
    a = list(arr)
    n = len(a)
    if n < 2:
        return a

    for i in range(n - 1):
        swapped = False
        # Move the maximum element of the unsorted portion to the end (index n-1-i) in each pass
        for j in range(0, n - 1 - i):
            if a[j] > a[j + 1]:
                a[j], a[j + 1] = a[j + 1], a[j]
                swapped = True
        if not swapped:
            break
    return a


def bubble_sort_inplace(a: List) -> List:
    """Sort the original list in-place and return its reference (in-place sorting).

    Example:
    >>> x = [3,2,1]
    >>> bubble_sort_inplace(x)
    [1,2,3]
    """
    n = len(a)
    if n < 2:
        return a

    for i in range(n - 1):
        swapped = False
        for j in range(0, n - 1 - i):
            if a[j] > a[j + 1]:
                a[j], a[j + 1] = a[j + 1], a[j]
                swapped = True
        if not swapped:
            break
    return a


__all__ = ["bubble_sort", "bubble_sort_inplace"]
