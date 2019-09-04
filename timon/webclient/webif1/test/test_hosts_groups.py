#!/usr/bin/env python

import timon.configure as script

group_by = [{
        "field": "lvl",
        "values": ["PROD", "QUAL", "OTHER"],
        "separator_style": "table",
        "default": "QUAL",
        },
    {
        "field": "styp",
        "values": ["MHCARE", "MHLINK", "Other"],
        "separator_style": "row",
        "default": "MHCARE",
        },
    {
        "field": "typ2",
        "values": ["1", "2"],
        "separator_style": "row",
        },
    ]


sample_data = {
    "n09": dict(typ2="2", lvl="QUAL", styp="MHCARE"),
    "n01": dict(typ2="1", lvl="PROD", styp="MHCARE"),
    "n07": dict(typ2="1", lvl="OTHER", styp="MHCARE"),
    "n08": dict(typ2="2", lvl="OTHER", styp="Other"),
    "n02": dict(typ2="1", lvl="PROD", styp="MHLINK"),
    "n04": dict(typ2="2", lvl="QUAL", styp="MHCARE"),
    "n03": dict(typ2="1", lvl="QUAL", styp="MHCARE"),
    "n05": dict(typ2="2", lvl="PROD", styp="Other"),
    "n06": dict(typ2="1", lvl="PROD", styp="MHCARE"),
    "n10": dict(typ2="2", lvl="PROD", styp="Other"),
}


def test_mk_nested_dict():
    rslt_test = {
    "QUAL": {
    "MHCARE": {
    "1": [
        "n03"
    ],
    "2": [
        "n04",
        "n09"
    ]
    }
    },
    "OTHER": {
    "Other": {
    "2": [
        "n08"
    ]
    },
    "MHCARE": {
    "1": [
        "n07"
    ]
    }
    },
    "PROD": {
    "Other": {
    "2": [
        "n05",
        "n10"
    ]
    },
    "MHLINK": {
    "1": [
        "n02"
    ]
    },
    "MHCARE": {
    "1": [
        "n01",
        "n06"
    ]
    }
    }
    }

    rslt = script.mk_nested_dict(group_by, sample_data)
    assert rslt == rslt_test

def test_dicdic2lisdic():
    rslt_test = [
        {
            "entries": [
                {
                    "entries": [
                        {
                            "entries": [
                                "n01",
                                "n06"
                            ],
                            "name": "1",
                            "separatur_style": "row"
                        },
                        {
                            "entries": [],
                            "name": "2",
                            "separatur_style": "row"
                        }
                    ],
                    "name": "MHCARE",
                    "separatur_style": "row"
                },
                {
                    "entries": [
                        {
                            "entries": [
                                "n02"
                            ],
                            "name": "1",
                            "separatur_style": "row"
                        },
                        {
                            "entries": [],
                            "name": "2",
                            "separatur_style": "row"
                        }
                    ],
                    "name": "MHLINK",
                    "separatur_style": "row"
                },
                {
                    "entries": [
                        {
                            "entries": [],
                            "name": "1",
                            "separatur_style": "row"
                        },
                        {
                            "entries": [
                                "n05",
                                "n10"
                            ],
                            "name": "2",
                            "separatur_style": "row"
                        }
                    ],
                    "name": "Other",
                    "separatur_style": "row"
                }
            ],
            "name": "PROD",
            "separatur_style": "table"
        },
        {
            "entries": [
                {
                    "entries": [
                        {
                            "entries": [
                                "n03"
                            ],
                            "name": "1",
                            "separatur_style": "row"
                        },
                        {
                            "entries": [
                                "n04",
                                "n09"
                            ],
                            "name": "2",
                            "separatur_style": "row"
                        }
                    ],
                    "name": "MHCARE",
                    "separatur_style": "row"
                },
                {
                    "entries": [
                        {
                            "entries": [],
                            "name": "1",
                            "separatur_style": "row"
                        },
                        {
                            "entries": [],
                            "name": "2",
                            "separatur_style": "row"
                        }
                    ],
                    "name": "MHLINK",
                    "separatur_style": "row"
                },
                {
                    "entries": [
                        {
                            "entries": [],
                            "name": "1",
                            "separatur_style": "row"
                        },
                        {
                            "entries": [],
                            "name": "2",
                            "separatur_style": "row"
                        }
                    ],
                    "name": "Other",
                    "separatur_style": "row"
                }
            ],
            "name": "QUAL",
            "separatur_style": "table"
        },
        {
            "entries": [
                {
                    "entries": [
                        {
                            "entries": [
                                "n07"
                            ],
                            "name": "1",
                            "separatur_style": "row"
                        },
                        {
                            "entries": [],
                            "name": "2",
                            "separatur_style": "row"
                        }
                    ],
                    "name": "MHCARE",
                    "separatur_style": "row"
                },
                {
                    "entries": [
                        {
                            "entries": [],
                            "name": "1",
                            "separatur_style": "row"
                        },
                        {
                            "entries": [],
                            "name": "2",
                            "separatur_style": "row"
                        }
                    ],
                    "name": "MHLINK",
                    "separatur_style": "row"
                },
                {
                    "entries": [
                        {
                            "entries": [],
                            "name": "1",
                            "separatur_style": "row"
                        },
                        {
                            "entries": [
                                "n08"
                            ],
                            "name": "2",
                            "separatur_style": "row"
                        }
                    ],
                    "name": "Other",
                    "separatur_style": "row"
                }
            ],
            "name": "OTHER",
            "separatur_style": "table"
        }
        ]
    rslt = script.mk_nested_dict(group_by, sample_data)
    rslt = script.dicdic2lisdic(rslt, group_by)
    assert rslt == rslt_test
