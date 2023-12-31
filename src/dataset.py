
import os
import multiprocessing
import time

import numpy as np

from mindspore.communication.management import init, get_rank, get_group_size
from mindspore.mindrecord import FileWriter
import mindspore.common.dtype as mstype
import mindspore.dataset as ds
import mindspore.dataset.vision.c_transforms as C
import mindspore.dataset.transforms.c_transforms as C2
from mindspore.dataset.vision import Inter

from src import datasets
from src.model_utils.config import config


def create_mindrecord_file(data, mindrecord_file, file_num=1):
    """Create MindRecord file."""
    writer = FileWriter(mindrecord_file, file_num)
    schema_json = {
        "image": {"type": "bytes"},
        "fid": {"type": "int32"},
        "pid": {"type": "int32"},
        "camid": {"type": "int32"}
    }
    writer.add_schema(schema_json, "schema_json")
    for fpath, fid, pid, camid in data:
        with open(fpath, 'rb') as f:
            img = f.read()
        row = {"image": img, "fid": fid, "pid": pid, "camid": camid}
        writer.write_raw_data([row])
    writer.commit()

def create_dataset(dataset_name, dataset_path, subset_name, batch_size=32, num_parallel_workers=4, distribute=False):
    """Create MindRecord Dataset"""
    ds.config.set_seed(1)
    subset = datasets.create(dataset_name, root=dataset_path, subset_name=subset_name)
    data = subset.data
    mindrecord_dir = os.path.join(config.mindrecord_dir, dataset_name)
    mindrecord_file = os.path.join(mindrecord_dir, subset_name + ".mindrecord")
    if not os.path.exists(mindrecord_file):
        if not os.path.isdir(mindrecord_dir):
            os.makedirs(mindrecord_dir)
        create_mindrecord_file(data, mindrecord_file)
    while not os.path.exists(mindrecord_file + ".db"):
        time.sleep(5)
    device_num, rank_id = _get_rank_info(distribute)
    num_parallel_workers = get_num_parallel_workers(num_parallel_workers)
    is_train = subset_name == "train"
    if device_num == 1:
        data_set = ds.MindDataset(mindrecord_file, columns_list=["image", "fid", "pid", "camid"], \
num_parallel_workers=num_parallel_workers, shuffle=is_train)
    else:
        data_set = ds.MindDataset(mindrecord_file, columns_list=["image", "fid", "pid", "camid"], \
num_shards=device_num, shard_id=rank_id, num_parallel_workers=num_parallel_workers, shuffle=is_train)
    #map operations on images
    decode_op = C.Decode()
    resize_op = C.Resize([384, 128], Inter.LINEAR)
    flip_op = C.RandomHorizontalFlip(prob=0.5)
    rescale_op = C.Rescale(1.0 / 255.0, 0.0)
    normalize_op = C.Normalize(mean=[0.485, 0.456, 0.406],
                               std=[0.229, 0.224, 0.225])
    swap_op = C.HWC2CHW()
    trans = []
    if is_train:
        trans += [decode_op,
                  resize_op,
                  flip_op,
                  rescale_op,
                  normalize_op,
                  swap_op]
    else:
        trans += [decode_op,
                  resize_op,
                  rescale_op,
                  normalize_op,
                  swap_op]
    data_set = data_set.map(operations=trans, input_columns=["image"], \
num_parallel_workers=num_parallel_workers)
    #map operations on labels
    type_cast_op = C2.TypeCast(mstype.int32)
    squeeze_op = np.squeeze
    trans = [type_cast_op, squeeze_op]
    data_set = data_set.map(operations=trans, input_columns=["fid"], \
num_parallel_workers=num_parallel_workers)
    data_set = data_set.map(operations=trans, input_columns=["pid"], \
num_parallel_workers=num_parallel_workers)
    data_set = data_set.map(operations=trans, input_columns=["camid"], \
num_parallel_workers=num_parallel_workers)
    # apply batch operations
    data_set = data_set.batch(batch_size, drop_remainder=is_train)
    return data_set, subset

def _get_rank_info(distribute):
    """get rank info"""
    if distribute:
        init()
        rank_id = get_rank()
        device_num = get_group_size()
    else:
        rank_id = 0
        device_num = 1
    return device_num, rank_id

def get_num_parallel_workers(num_parallel_workers):
    """
    Get num_parallel_workers used in dataset operations.
    If num_parallel_workers > the real CPU cores number, set num_parallel_workers = the real CPU cores number.
    """
    cores = multiprocessing.cpu_count()
    if isinstance(num_parallel_workers, int):
        if cores < num_parallel_workers:
            print("The num_parallel_workers {} is set too large, now set it {}".format(num_parallel_workers, cores))
            num_parallel_workers = cores
    else:
        print("The num_parallel_workers {} is invalid, now set it {}".format(num_parallel_workers, min(cores, 8)))
        num_parallel_workers = min(cores, 8)
    return num_parallel_workers

if __name__ == "__main__":
    pass
