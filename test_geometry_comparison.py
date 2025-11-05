from shapely.geometry import Polygon, MultiPolygon
from geometry_comparison import compare_geometries


def assert_scores(result, status="compared", polygon=None, line=None, overall=None, msg=""):
    """Helper to assert comparison results with less repetition"""
    assert result["status"] == status, f"{msg}: status mismatch"
    if polygon is not None:
        if callable(polygon):
            assert polygon(result["polygon_score"]), f"{msg}: polygon_score={result['polygon_score']}"
        else:
            assert result["polygon_score"] == polygon, f"{msg}: polygon_score={result['polygon_score']}"
    if line is not None:
        if callable(line):
            assert line(result["line_score"]), f"{msg}: line_score={result['line_score']}"
        else:
            assert result["line_score"] == line, f"{msg}: line_score={result['line_score']}"
    if overall is not None:
        if callable(overall):
            assert overall(result["overall_score"]), f"{msg}: overall_score={result['overall_score']}"
        else:
            assert result["overall_score"] == overall, f"{msg}: overall_score={result['overall_score']}"


def test_two_triangles_vs_rectangle():
    rect = Polygon([(0, 0), (0.5, 0), (0.5, 0.5), (0, 0.5)])
    tri1 = Polygon([(0, 0), (0.5, 0), (0.5, 0.5)])
    tri2 = Polygon([(0, 0), (0.5, 0.5), (0, 0.5)])
    two_triangles = MultiPolygon([tri1, tri2])

    result = compare_geometries(rect, rect)
    assert_scores(result, polygon=0.0, line=lambda x: x < 1e-10, overall=lambda x: x < 1e-10)

    result = compare_geometries(two_triangles, rect)
    assert_scores(result, polygon=0.0, line=lambda x: x > 0.2)

    result = compare_geometries(tri1, rect)
    assert_scores(result, polygon=0.125, line=lambda x: x > 0.1)


def test_zero_area_vs_thin_rectangle():
    rect = Polygon([(0, 0), (0.5, 0), (0.5, 0.001), (0, 0.001)])
    zero = Polygon([(0, 0), (0.4, 0), (0.5, 0), (0.5, 0.001), (0.4, 0.001), (0.4, 0)])

    result = compare_geometries(zero, rect)
    print(result)
    assert_scores(result, polygon=lambda x: x < 1e-2, line=lambda x: x < 1e-2, overall=lambda x: x < 1e-2)

if __name__ == "__main__":
    test_two_triangles_vs_rectangle()
    test_zero_area_vs_thin_rectangle()
    print("All tests passed!")
