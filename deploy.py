from subprocess import call
import os
import platform

c_dir = os.path.dirname(os.path.abspath(__file__))
h_dir = os.getenv("HOME")
script_destination_dir = '/usr/local/bin/'

def remove_symlinks_or_file(name):
    print "\tRemoving file: %s" % os.path.join(h_dir, name)
    call(["rm", os.path.join(h_dir, name)])


def symlink_file(name):
    print "\tSymlinking file into home: %s" % os.path.join(c_dir, name)
    call(["ln", "-s", os.path.join(c_dir, name), h_dir])


def symlink_script(sname, dest_dir):
    print "\tCopying script '%s' into %s" % (sname, dest_dir)
    call(['sudo', 'ln', '-s', os.path.join(c_dir, 'scripts/' + sname), dest_dir])

def create_file(name):
    print "\tCreating file: %s" % os.path.join(h_dir, name)
    call(["touch", os.path.join(h_dir, name)])


def create_dir(name):
    try:
        os.mkdir(os.path.join(h_dir, ".tmp"))
        print "\tCreated dir: %s" % os.path.join(h_dir, name)
    except (OSError) as (errno, strerror):
        if errno != 17:  # fine if file exists
            raise
        print "\tDir already exists: %s" % os.path.join(h_dir, name)


def clone_git_repo(prefix_prot, target_dir, repo):
    print "\tTrying to clone from %s to %s" % ('github.com/' + repo, os.path.join(c_dir, target_dir))
    try:
        os.makedirs(os.path.join(c_dir, target_dir))
    except (OSError) as (errno, strerror):
        if errno != 17:  # fine if file exists
            raise
        return

    call(["git", "clone", prefix_prot + repo, os.path.join(c_dir, target_dir)])


def setup_vim():
    call(['gvim', '-f', '+BundleInstall', '+qall'])


def _print_section(sname):
    print '\n%s\n' % sname


if __name__ == '__main__':
    print "Home directory found: %s" % h_dir
    print "Current directory found: %s" % c_dir

    rc_file = ['.vimrc', '.gitconfig', '.gvimrc', '.hgrc', '.vim', '.bashrc', '.bash_profile', '.pylintrc', '.tmux.conf']

    _print_section("Remove rc files or symlinks if they exist already.")
    for fname in rc_file:
        remove_symlinks_or_file(fname)

    _print_section("Symlinking rc files into home directory.")
    for fname in rc_file:
        symlink_file(fname)

    loc_rc_file = [".extvimrc", ".localbashrc"]
    _print_section("Create empty local rc files.")
    for fname in loc_rc_file:
        create_file(fname)

    dirs = [".tmp"]
    _print_section("Creating directories (if they don't exist already).")
    for dname in dirs:
        create_dir(dname)

    script_names = ['clj', 'hgdiff']
    _print_section("Copying scripts into %s" % script_destination_dir)
    for sname in script_names:
        symlink_script(sname, script_destination_dir)

    https_t_dir_repos = [
        ['.vim/bundle/vundle/', 'gmarik/vundle/'],
    ]

    _print_section("Cloning git repositories (https).")
    for (target_dir, repo) in https_t_dir_repos:
        clone_git_repo("https://github.com/", target_dir, repo)

    ssh_t_dir_repos = [
        ['.vim/pathogen/harlequin', 'nielsmadan/harlequin'],
        ['.vim/pathogen/geisha', 'nielsmadan/geisha'],
        ['.vim/pathogen/venom', 'nielsmadan/venom'],
        ['.vim/pathogen/mercury', 'nielsmadan/mercury'],
    ]

    _print_section("Cloning git repositories (git+ssh).")
    for (target_dir, repo) in ssh_t_dir_repos:
        clone_git_repo("git+ssh://git@github.com/", target_dir, repo)

    _print_section("Setup vim.")
    setup_vim()
