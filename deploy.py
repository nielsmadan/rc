from subprocess import call
import os

c_dir = os.path.dirname(os.path.abspath(__file__))
h_dir = os.getenv("HOME")

print "Home directory found: %s" % h_dir
print "current directory found: %s\n" % c_dir

print "Symlinking rc files into home directory"
rc_file = ['.vimrc', '.gvimrc', '.hgrc', '.vim', '.bashrc', '.pylintrc']

print "Remove rc files or symlinks if they exist already."
for f in rc_file:
    call(["rm", os.path.join(h_dir, f)])

for f in rc_file:
    call(["ln", "-s", os.path.join(c_dir, f), h_dir])

loc_rc_file = [".extvimrc", ".localbashrc"]
print "Create local rc files."
for f in loc_rc_file:
    call(["touch", os.path.join(h_dir, f)])

print "create bundle/vundle directory in .vim and git clone it"
call(["mkdir", "-p", os.path.join(c_dir, ".vim/bundle/vundle")])
call(["git", "clone", "https://github.com/gmarik/vundle/", os.path.join(c_dir, ".vim/bundle/vundle")])
