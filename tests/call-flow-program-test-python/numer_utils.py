"""Utility helpers used as a richer example for call flow testing."""

from typing import Callable, Dict, Iterable, Iterator, List

BucketMap = Dict[str, List[int]]
Handler = Callable[[int, BucketMap], None]

NOISE_SENTINELS = {-999, 999}
CHUNK_SIZE = 3


def normalize_value(value: int) -> int:
    """Ensure the provided value behaves like an integer."""
    return int(value)


def ensure_sequence(numbers: Iterable[int]) -> List[int]:
    """Materialize the incoming iterable to allow multi-pass processing."""
    if isinstance(numbers, list):
        return numbers
    return [normalize_value(candidate) for candidate in numbers]


def initialize_tracker() -> BucketMap:
    """Pre-create buckets so repeated lookups are consistent."""
    return {bucket: [] for bucket in ("zero", "negative", "even", "odd", "noise")}


def preprocess_numbers(numbers: Iterable[int], tracker: BucketMap) -> List[int]:
    """Filter, normalize, and expand numbers before classification."""
    prepared: List[int] = []
    for index, candidate in enumerate(ensure_sequence(numbers)):
        value = normalize_value(candidate)
        if is_noise(value):
            _route_noise(value, tracker, index)
            continue
        prepared.extend(_expand_candidate(value, index))
    return prepared


def is_noise(value: int) -> bool:
    return value in NOISE_SENTINELS


def _route_noise(value: int, tracker: BucketMap, index: int) -> None:
    bucket = _noise_bucket_preference(value, index)
    _store(bucket, value, tracker)


def _noise_bucket_preference(value: int, index: int) -> str:
    if index % 2 == 0 and is_negative(value):
        return "negative"
    if value > 0:
        return "odd"
    return "noise"


def _expand_candidate(value: int, index: int) -> List[int]:
    if _should_duplicate(value, index):
        return [value, value + 1]
    return [value]


def _should_duplicate(value: int, index: int) -> bool:
    if is_zero(value):
        return False
    if index % 3 == 0 and is_even(value):
        return True
    if is_negative(value) and abs(value) % 2 == 1:
        return True
    return False


def is_zero(value: int) -> bool:
    """Return True when the normalized value is zero."""
    return normalize_value(value) == 0


def is_negative(value: int) -> bool:
    """Return True when the normalized value is negative."""
    return normalize_value(value) < 0


def is_even(value: int) -> bool:
    """Return True when the normalized value is even."""
    return normalize_value(value) % 2 == 0


def describe_number(value: int) -> str:
    """Classify the number into one of the supported bucket names."""
    if is_zero(value):
        return "zero"
    if is_negative(value):
        return "negative"
    if is_even(value):
        return "even"
    return "odd"


def chunk_numbers(numbers: List[int], chunk_size: int = CHUNK_SIZE) -> Iterator[List[int]]:
    """Yield fixed-size chunks to create nested loop structures."""
    chunk: List[int] = []
    for number in numbers:
        chunk.append(number)
        if len(chunk) == chunk_size:
            yield chunk[:]
            chunk.clear()
    if chunk:
        yield chunk[:]


def resolve_strategy(bucket: str, number: int) -> Handler:
    """Resolve handler, falling back to additional logic when required."""
    handler = STRATEGIES.get(bucket)
    if handler:
        return handler
    return _fallback_strategy(bucket, number)


def _fallback_strategy(bucket: str, number: int) -> Handler:
    if bucket == "negative" and is_even(number):
        return _handle_even
    return _handle_odd


def evaluate_chunk_for_side_effects(chunk: List[int], tracker: BucketMap) -> None:
    """Iterate with a while loop to add more control flow variety."""
    position = 0
    while position < len(chunk):
        candidate = chunk[position]
        _maybe_trigger_followup(candidate, tracker)
        position += 1


def _maybe_trigger_followup(number: int, tracker: BucketMap) -> None:
    if number == 0:
        _invoke_followup_chain("zero", number, tracker)
    elif number % 5 == 0:
        _invoke_followup_chain("noise", number, tracker)
    else:
        _invoke_nested_alternative(number, tracker)


def _invoke_followup_chain(kind: str, number: int, tracker: BucketMap) -> None:
    _log_followup(kind, number)
    if kind == "zero":
        _handle_zero(number, tracker)
    elif kind == "noise":
        _store("noise", -number, tracker)
    else:
        _store(kind, number, tracker)


def _log_followup(kind: str, number: int) -> None:
    print(f"Follow-up for {number} classified as {kind}")


def _invoke_nested_alternative(number: int, tracker: BucketMap) -> None:
    if is_negative(number):
        if is_even(number):
            _handle_even(number, tracker)
        else:
            _handle_negative(number, tracker)
    else:
        if number % 3 == 0:
            _handle_odd(number, tracker)
        else:
            _handle_even(number + 1, tracker)
    if number % 7 == 0:
        _store("noise", number, tracker)
    elif number > 10:
        _store("odd", number, tracker)


def dispatch(handler: Handler, number: int, tracker: BucketMap) -> None:
    _log_dispatch(handler, number)
    handler(number, tracker)
    if _exceeds_threshold(number):
        _handle_threshold_crossed(number, tracker)


def _log_dispatch(handler: Handler, number: int) -> None:
    print(f"Dispatching {number} via {handler.__name__}")


def _exceeds_threshold(number: int) -> bool:
    return abs(number) > 50


def _handle_threshold_crossed(number: int, tracker: BucketMap) -> None:
    _store("noise", number, tracker)


def _store(bucket: str, number: int, tracker: BucketMap) -> None:
    """Persist the number into the requested bucket with logging."""
    tracker.setdefault(bucket, []).append(number)
    _log_bucket_change(bucket, number)


def _log_bucket_change(bucket: str, number: int) -> None:
    print(f"Added {number} to '{bucket}' bucket.")


def finalize_tracker(tracker: BucketMap) -> BucketMap:
    for bucket, values in list(tracker.items()):
        tracker[bucket] = _apply_bucket_postprocessing(bucket, values)
    _summarize_tracker(tracker)
    return tracker


def enforce_balance(tracker: BucketMap) -> None:
    """Run a compact while loop that shuffles entries based on simple heuristics."""
    iteration = 0
    while iteration < 2:
        for bucket in ("even", "odd"):
            _rebalance_bucket(bucket, tracker, iteration)
        iteration += 1


def _rebalance_bucket(bucket: str, tracker: BucketMap, iteration: int) -> None:
    values = tracker.get(bucket, [])
    if not values:
        return
    pivot = values[iteration % len(values)]
    if bucket == "even":
        if iteration == 0:
            _store("even", pivot, tracker)
        else:
            _store("noise", pivot, tracker)
    else:
        if pivot % 3 == 0:
            _store("odd", pivot, tracker)
        else:
            _store("noise", -pivot, tracker)


def _apply_bucket_postprocessing(bucket: str, values: List[int]) -> List[int]:
    unique = sorted(set(values))
    if bucket == "negative":
        return [value for value in unique if value < 0]
    return unique


def _summarize_tracker(tracker: BucketMap) -> None:
    counts = {bucket: len(values) for bucket, values in tracker.items()}
    print(f"Current counts: {counts}")


def _handle_zero(number: int, tracker: BucketMap) -> None:
    _store("zero", number, tracker)


def _handle_negative(number: int, tracker: BucketMap) -> None:
    _store("negative", number, tracker)


def _handle_even(number: int, tracker: BucketMap) -> None:
    _store("even", number, tracker)


def _handle_odd(number: int, tracker: BucketMap) -> None:
    _store("odd", number, tracker)


STRATEGIES: Dict[str, Handler] = {
    "zero": _handle_zero,
    "negative": _handle_negative,
    "even": _handle_even,
    "odd": _handle_odd,
}


def classify_numbers(numbers: Iterable[int]) -> BucketMap:
    """
    Classify numbers and dispatch the work through a handler map.
    Intended to provide a richer call graph than ``even_or_odd``.
    """
    tracker = initialize_tracker()
    prepared = preprocess_numbers(numbers, tracker)
    for chunk in chunk_numbers(prepared):
        for number in chunk:
            bucket = describe_number(number)
            handler = resolve_strategy(bucket, number)
            dispatch(handler, number, tracker)
        evaluate_chunk_for_side_effects(chunk, tracker)
    enforce_balance(tracker)
    return finalize_tracker(tracker)


if __name__ == "__main__":
    SAMPLE_DATA = [0, 1, 2, -3, -4, 9, -999, 999, 50, 51]
    CLASSIFIED = classify_numbers(SAMPLE_DATA)
    print(CLASSIFIED)
