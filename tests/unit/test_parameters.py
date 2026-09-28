from bci2000_bids.bci2000.parameters import flatten_values, parameter_values, parse_numeric


def test_parameter_numeric_units_and_expressions():
    assert parse_numeric("10mA") == 10
    assert parse_numeric("1e-3") == 0.001
    assert parse_numeric("StimulusCode==1") is None


def test_parameter_aliases_and_nested_values():
    assert parameter_values({"Source.SamplingRate": "2000"}, "SamplingRate", ("Source.SamplingRate",)) == "2000"
    assert flatten_values(["1", ["2", "3"]]) == ["1", "2", "3"]
