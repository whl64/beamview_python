# oldpath="$PATH"

# __conda_setup="$('/home/lo_li/mambaforge/bin/conda' 'shell.bash' 'hook' 2> /dev/null)"
# if [ $? -eq 0 ]; then
#     eval "$__conda_setup"
# else
#     if [ -f "/home/lo_li/mambaforge/etc/profile.d/conda.sh" ]; then
#         . "/home/lo_li/mambaforge/etc/profile.d/conda.sh"
#     else
#         export PATH="/home/lo_li/mambaforge/bin:$PATH"
#     fi
# fi
# unset __conda_setup

# if [ -f "/home/lo_li/mambaforge/etc/profile.d/mamba.sh" ]; then
#     . "/home/lo_li/mambaforge/etc/profile.d/mamba.sh"
# fi

# mamba activate python3.10
# python beamview_python.py
# mamba deactivate
# mamba deactivate

# export PATH="$oldpath"

/home/lo_li/mambaforge/envs/python3.10/bin/python3.10 beamview_python.py