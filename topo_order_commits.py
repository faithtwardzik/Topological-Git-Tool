import sys
import os
import zlib

class CommitNode:
    def __init__(self, commit_hash):
        """
        :type commit_hash: str
        """
        self.commit_hash = commit_hash
        self.parents = list() 
        self.children = list() 

###########

# find parent hashes given the decoded commit's file as string
def find_parents(str_obj):

    parent_ind = 0
    par_hashes = []
    more_to_find = True;
    start = 0

    end = str_obj.find("author", start)
    while more_to_find:
        parent_ind = str_obj.find("parent ", start, end)
        if parent_ind == -1:
            break
        hash_offset = 7
        hash_start = parent_ind + hash_offset
        
        # find the end index of the hash
        for k in range(hash_start, len(str_obj)):
            if str_obj[k] == '\n':
                hash_end = k - 1
                break
        par_hashes.append(str_obj[hash_start:hash_end + 1])

        # update the start point to search for next parent
        start = parent_ind + hash_offset

    return par_hashes

###########

# DFS to topologically sort the commits
def get_topo_ordered_commits(root_vertices, found):
    order = []

    # visited is the union of the gray and black vertices  
    visited = set()
    gray_stack = []
    stack = list(root_vertices)
 
    while stack:
        v = stack.pop()
        if v in visited:
            continue
        visited.add(v)

        # v is not a child of the vertex on the top of the gray stack
        while (gray_stack and v not in found[gray_stack[-1]].children):
            g = gray_stack.pop()
            order.append(g)

        gray_stack.append(v)
        for c in found[v].children:
            if c in visited:
                continue
            stack.append(c)
    
    # unload the gray_stack onto sorted list in REVERSE order
    while (gray_stack):
        order.append(gray_stack.pop())
    
    return order

###########

# prints the topologically sorted commits in order 
def print_topo_ordered_commits(ordered, root_commits_print, found):

    for i in range(0, len(ordered)):

        # if on last commit, do not check if next com = parent
        if i == len(ordered) - 1:
            if ordered:
                print(ordered[-1] + " ", end=(''))
                if ordered[-1] in root_commits_print:
                    print(root_commits_print[ordered[-1]], end='')
                print()
                return
 
        com_curr = ordered[i]
        com_next = ordered[i + 1]

        print(com_curr, end=(''))

        # print branch next to hash, if applicable
        if com_curr in root_commits_print:
            print(" " + root_commits_print[com_curr])
        else:
            print()

        curr_parents = found[com_curr].parents
        next_children = found[com_next].children

        # if next node is not one of curr node's parents = sticky situation
        if not com_next in curr_parents:
            count = 0
            # print parents before sticky end
            for parent in curr_parents:
                if count == len(curr_parents) - 1:
                    print(parent, end=(""))
                else:
                    print(parent, end=(" "))
                count += 1

            # sticky end & start
            print("=\n\n=", end=(''))

            # print children after sticky start
            for child in next_children:
                print(child, end=(" "))
            print("\n", end=(''))

###########

# recursively get the aliases for local branches, works on dirs as well
def get_loc_branches(dir, loc_br_aliases, local_branches):

    with os.scandir(dir) as it:
        for item in it:
            if item.is_dir():
                get_loc_branches(item.path, loc_br_aliases, local_branches)
            elif item.is_file():
                loc_br = os.path.relpath(item.path, local_branches) 
                loc_br_aliases.append(loc_br)

###########

# find the toplevel Git rep location 
def find_toplev_Git():

    toplevel = ""
    cwd_list = os.listdir()
    
    # check if curr directory is toplevel rep location
    for i in range(0, len(cwd_list)):
        if cwd_list[i] == ".git":
            toplevel = os.getcwd()
            break

    abs_path = os.getcwd()

    # continue to move up a directory until toplevel found
    while toplevel == "":
        abs_path = os.path.dirname(abs_path)
        if not os.path.isdir(abs_path):
            sys.stderr.write("Not inside a Git repository")
            exit(1)
        abs_path_list = os.listdir(abs_path)
        for k in range(0, len(abs_path_list)):
            if abs_path_list[k] == ".git":
                toplevel = abs_path

    return toplevel

###########

def topo_order_commits():
    
    toplevel = find_toplev_Git()

    #location of the local branches
    local_branches = toplevel + "/.git/refs/heads"
    
    loc_br_aliases = list()
    get_loc_branches(local_branches, loc_br_aliases, local_branches) 

    stack = []
    found = {}
    root_commits_print = {}
    root_commits = []

    # get the branch commit hashes, turn into CommitNodes, add to found dictionary & root commits
    for loc_branch in loc_br_aliases:
        branch_file = open(local_branches + "/" + loc_branch, 'r')
        com_hash = branch_file.readline().rstrip()
        stack.append(com_hash)
        if not com_hash in found:
            found[com_hash] = CommitNode(com_hash)
        if not com_hash in root_commits_print:
            root_commits_print[com_hash] = loc_branch
        else:
            root_commits_print[com_hash] = root_commits_print[com_hash] + " " + loc_branch
   
    visited = set()

    while stack:
        par_branch = stack.pop()

        # if it's been visited, do nothing
        if par_branch in visited:
            continue

        visited.add(par_branch)

        # open file with parents of curr commit
        abs_path = toplevel + "/.git/objects/" + par_branch[0:2] + "/" + par_branch[2:len(par_branch)]
        ch_commit = open(abs_path, "rb").read()
        ch_commit = zlib.decompress(ch_commit)
        ch_commit = str(ch_commit, 'utf-8')
    
        par_hashes = find_parents(ch_commit)
    
        # if no parents, add to root commits
        if (len(par_hashes) == 0):
           root_commits.append(par_branch)

        # if commit hashes not in found, create CommitNodes and add to stack 
        for m in range(0, len(par_hashes)):
            if not par_hashes[m] in found:
                found[par_hashes[m]] = CommitNode(par_hashes[m])
                stack.append(par_hashes[m])

            parent = found[par_hashes[m]]

            # add parent commits to children and child commits to parents
            if par_branch not in parent.children:
                parent.children.append(par_branch)
            if par_hashes[m] not in found[par_branch].parents:
                found[par_branch].parents.append(par_hashes[m])

        for key in found:
            found[key].children.reverse()

    ordered = get_topo_ordered_commits(root_commits, found)

    print_topo_ordered_commits(ordered, root_commits_print, found)


if __name__ == '__main__':
    topo_order_commits()
