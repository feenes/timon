def get_data(fieldname, entry):
    field = fieldname.split(".")
    rslt = entry
    for data in field:
        if rslt[data]:
            rslt = rslt[data]
    return rslt


def cnvt_grpby_to_nested_dict(grpby, entries):
    """
    Create a dict of dict of grpby arguments with sorted
    entries at the end of nested dict
    """
    rslt = {}
    print("rslt = %8x" % id(rslt))
    for key, entry in entries.items():
        target = rslt
        for grp_info in grpby[:-1]:
            fieldname = grp_info["field"]
            # dflt_val = grp_info.get("default", grp_info["values"][0])
            field = get_data(fieldname, entry)
            if field not in target:
                target[field] = {}
                print("create {} %x for field %8s in %x" % (
                      id(target[field]), field, id(target)))
            target = target[field]

        # Handle last group differenty
        grp_info = grpby[-1]
        fieldname = grp_info["field"]
        # dflt_val = grp_info.get("default", grp_info["values"][0])
        field = get_data(fieldname, entry)
        if field not in target:
            target[field] = []
        target = target[field]
        target.append(key)
        target.sort()
    return rslt


def cnvt_nested_grpby_to_lst_dict(dicdic, grpby, lvl=0):
    """
    Recursive func that transform nested dict created by
    cnvt_grpby_to_nested_dict to list of dicts with
    good order define in grpby
    """
    grp = grpby[lvl]
    grpvals = grp["values"]

    def keyfunc(key):
        if key in grpvals:
            return grpvals.index(key)
        else:
            return len(grpvals)+1

    # if isinstance(dicdic, dict):
    #     keys = sorted(dicdic.keys(), key=keyfunc)
    # else:
    #     keys = sorted(dicdic)

    if lvl < len(grpby):
        rslt = []
        # for key in keys:
        for key in grpvals:
            if lvl < len(grpby) - 1:
                subentries = cnvt_nested_grpby_to_lst_dict(
                    dicdic.get(key, {}), grpby, lvl+1)
            else:
                subentries = dicdic.get(key, [])
            entry = dict(
                name=key,
                separator_style=grp["separator_style"],
                entries=subentries
                )
            rslt.append(entry)
        return rslt

    return dict(last=dicdic)
