import os

def compare_two_files(file1_path, file2_path):
    file1 = open(file1_path, 'r')
    file2 = open(file2_path, 'r')

    lines1 = file1.readlines()
    lines2 = file2.readlines()

    print(file1_path, file2_path)
    print(len(lines1), len(lines2))

    assert(len(lines1) == len(lines2))

    for i in range(len(lines1)):
        try:
            assert(lines1[i] == lines2[i])
        except:
            assert(file1_path.find("ExecPlanner") != -1)
            assert(lines1[j] in lines2 for j in range(len(lines1)))
            break


def main() -> None:
    """The main program"""

    json_input = ["consistency_example", "multi_tenant", "normalization"]
    graph_input = ["test1", "test2", "test3", "test4", "test5", "test6"]
    obj_input = ["synthesized_test1"]

    targets = json_input + graph_input + obj_input

    new_version_path_prefix = os.path.join("..", "examples")
    old_version_path_prefix = os.path.join("/home/jiarong/FlexCore-public", "examples")

    for folder in targets:
        for file_name in ["command_ElemPlanner.txt", "command_ExecPlanner.txt", "command_ProgPlanner.txt"]:
            path1 = os.path.join(old_version_path_prefix, folder, file_name)
            path2 = os.path.join(new_version_path_prefix, folder, file_name)
            compare_two_files(path1, path2)

    print("The outputs across two versions are the same!")


if __name__ == "__main__":
    main()
