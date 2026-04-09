def convert_gumtree_res(ts_res) -> list[tuple[int, int, int, int, str]]:
    res = []
    for line in ts_res:
        tmp = []
        status = str(line[0])
        match status:
            case "insert":
                tmp.extend(list(map(lambda x: int(str(x)), line[1:5])))
                tmp.append(str(line[5]))
            case "update":
                tmp.extend(list(map(lambda x: int(str(x)), line[1:5])))
                tmp.append("")
            case "delete":
                tmp.extend(list(map(lambda x: int(str(x)), line[1:3])))
                tmp.extend([-1, -1, ""])
        res.append(tuple(tmp))

    return res
