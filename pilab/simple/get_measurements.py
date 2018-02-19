from machine_simple_meter import MachineSimpleMeter
bitscope = MachineSimpleMeter()


bitscope.s_find_device()
bitscope.s_check_model()
bitscope.s_setup_bs()
bitscope.s_dump()
while (True):
    bitscope.s_process_and_req()
    bitscope.s_dump()
    bitscope.derive_voltage()
    print bitscope.data['voltage']
