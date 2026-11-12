```
```python
def median_absolute_deviation(xs):
    """Calculate the median absolute deviation of a list of numbers."""
    if not xs:
        raise ValueError("Input list must be non-empty")
    
    # Sort the list
    sorted_xs = sorted(xs)
    n = len(sorted_xs)
    median = sorted_xs[n // 2]
    
    # Calculate the absolute deviations
    abs_deviations = [abs(x - median) for x in sorted_xs]
    
    # Sort the absolute deviations
    sorted_abs_deviations = sorted(abs_deviations)
    m = len(sorted_abs_deviations)
    median_abs_deviation = sorted_abs_deviations[m // 2]
    
    return median_abs_deviation

if __name__ == '__main__':
    result = median_absolute_deviation([1, 1, 2, 2, 4, 6, 9])
    print(f"Median absolute deviation of [1, 1, 2, 2, 4, 6, 9]: {result}")
```

Not confirmed: No source could be read. huggingface search 'median absolute deviation code' failed: HTTPSConnectionPool(host='huggingface.co', port=443): Read timed out. (read timeout=30)

## Not confirmed by the team
- s1 (researcher): Find the definition of median absolute deviation and its implementation in Python. - no source could be read: huggingface search 'median absolute deviation' failed: HTTPSConnectionPool(host='huggingface.co', port=443): Read timed out. (read timeout=30)
- s2 (coder): Implement the median absolute deviation function in Python, including the self-test. - OSError: We couldn't connect to 'https://huggingface.co' to load the files, and couldn't find them in the cached files.
Check your internet connection or see how to run the library in offline mode at 'https://huggingface.co/docs/transformers/installation#offline-mode'.
- s3 (browser): Visit the HuggingFace page for the median absolute deviation implementation and verify the code. - browser could not finish: Error: It looks like you are using Playwright Sync API inside the asyncio loop.
Please use the Async API instead.
- s4 (coder): Update the `mad.py` file with the verified implementation and self-test. - OSError: We couldn't connect to 'https://huggingface.co' to load the files, and couldn't find them in the cached files.
Check your internet connection or see how to run the library in offline mode at 'https://huggingface.co/docs/transformers/installation#offline-mode'.
- s2r (researcher): Implement the median absolute deviation function in Python, including the self-test, using offline mode or local data sources - no source could be read: huggingface search 'median absolute deviation definition' failed: HTTPSConnectionPool(host='huggingface.co', port=443): Read timed out. (read timeout=30)
- s3r (researcher): Download and implement the median absolute deviation function using HuggingFace's API for code retrieval, then verify the implementation. - no source could be read: huggingface search 'median absolute deviation code' failed: HTTPSConnectionPool(host='huggingface.co', port=443): Read timed out. (read timeout=30)
- s4r (researcher): Write a Python function median_absolute_deviation(xs) that returns the median absolute deviation of a non-empty list of numbers. Save it as mad.py in  - no source could be read: huggingface search 'median absolute deviation code' failed: HTTPSConnectionPool(host='huggingface.co', port=443): Read timed out. (read timeout=30)