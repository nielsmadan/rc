from subprocess import call
import os

c_dir = os.path.dirname(os.path.abspath(__file__))
h_dir = os.getenv("HOME")

print "Home directory found: %s" % h_dir
print "current directory found: %s\n" % c_dir

rc_file = ['.vimrc', '.gvimrc', '.hgrc', '.vim', '.bashrc', '.pylintrc']

print "Remove rc file symlinks."
for f in rc_file:
    call(["rm", os.path.join(h_dir, f)])
