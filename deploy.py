from subprocess import call
import os
import platform

c_dir = os.path.dirname(os.path.abspath(__file__))
h_dir = os.getenv("HOME")

if platform.system() == 'Linux':
    symlink_file_cmd = ['ln', '-s']
    symlink_dir_cmd = ['ln', '-s']

print "Home directory found: %s" % h_dir
print "Current directory found: %s" % c_dir

rc_file = ['.vimrc', '.gvimrc', '.hgrc', '.vim', '.bashrc', '.pylintrc']

print ""
print "Remove rc files or symlinks if they exist already."
for f in rc_file:
    call(["rm", os.path.join(h_dir, f)])

print ""
print "Symlinking rc files into home directory"
for f in rc_file:
    call(["ln", "-s", os.path.join(c_dir, f), h_dir])

loc_rc_file = [".extvimrc", ".localbashrc"]
print "Create local rc files."
for f in loc_rc_file:
    call(["touch", os.path.join(h_dir, f)])

print "create bundle/vundle directory in .vim and git clone it"
os.makedirs(os.path.join(c_dir, ".vim/bundle/vundle"))
call(["git", "clone", "https://github.com/gmarik/vundle/", os.path.join(c_dir, ".vim/bundle/vundle")])

print "create .tmp directory"
os.mkdir(os.path.join(h_dir, ".tmp"))
