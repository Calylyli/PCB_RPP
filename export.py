
import os
import numpy as np
import mindspore as ms
from mindspore import Tensor, context, load_checkpoint, load_param_into_net, export

from src.pcb import PCB_infer
from src.rpp import RPP_infer

from src.model_utils.config import config
from src.model_utils.device_adapter import get_device_id
from src.model_utils.moxing_adapter import moxing_wrapper

def build_model():
    model = None
    if config.model_name == "PCB":
        model = PCB_infer()
    elif config.model_name == "RPP":
        model = RPP_infer()
    return model

def modelarts_pre_process():
    '''modelarts pre process function.'''
    config.file_name = os.path.join(config.output_path, config.file_name)

@moxing_wrapper(pre_process=modelarts_pre_process)
def run_export():
    """run export."""
    context.set_context(mode=context.GRAPH_MODE, device_target=config.device_target)
    if config.device_target == "Ascend":
        context.set_context(device_id=get_device_id())
    # define network
    network = build_model()
    assert config.checkpoint_file_path is not None, "checkpoint_path is None."
    # load network checkpoint
    param_dict = load_checkpoint(config.checkpoint_file_path)
    load_param_into_net(network, param_dict)
    # export network
    inputs = Tensor(np.zeros([config.batch_size, 3, config.image_height, config.image_width]), ms.float32)
    export(network, inputs, file_name=config.file_name, file_format=config.file_format)

if __name__ == '__main__':
    run_export()
