# Add data models to python path

MOD_PCB_TM_BASE=$(echo "$PWD" | sed -E 's|(.*?/module_pcb_thermal_mockup/).*|\1|')
export MOD_PCB_TM_BASE

export PYTHONPATH=$PYTHONPATH:$MOD_PCB_TM_BASE

echo "Set PYTHONPATH"
echo $PYTHONPATH

# Add environment variables from env.py