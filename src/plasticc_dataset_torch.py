from pathlib import Path
from tqdm import tqdm
import numpy as np
import pandas as pd
import torch
from plasticc_create_lightcurves import make_lc_tensor

class PLAsTiCC_Torch_Dataset_Lazy(torch.utils.data.Dataset):
    """
    Dataset that loads light curves on-demand 
    Individual light curves pt files (torch) should reside in path_to_light_curves (see __init__)
    """
    
    def __init__(self, path_to_light_curves, plasticc_ids, lc_labels, is_test=False):
        
    
        self.path = path_to_light_curves
        self.plasticc_ids = plasticc_ids
        self.lc_labels = lc_labels        
        self.is_test = is_test
        self.data_size = len(plasticc_ids)
        
    def __len__(self):
        return self.data_size
    
    def __getitem__(self, idx):
        
        with open(self.path / f'{self.plasticc_ids[idx]}.pt', 'rb') as f:
            lc_torch = torch.load(f)
        
        return lc_torch, self.lc_labels[idx]


class PLAsTiCC_Torch_Dataset_Eager(torch.utils.data.Dataset):
    """
    Dataset that loads all light curves in RAM
    Expects a pandas dataframe of the plasticc light curve files
    """
    
    def __init__(self, df_data, plasticc_ids, lc_labels, is_test=False, max_lc_length=72, detected_only=False):
        
        self.plasticc_ids = plasticc_ids
        self.lc_labels = lc_labels        
        self.is_test = is_test
        self.data_size = len(plasticc_ids)
        
        print("Creating tensors from light curves")
        self.lc_torch = []
        for lc_id in tqdm(plasticc_ids):
            self.lc_torch.append(make_lc_tensor(df_data.loc[lc_id].values, max_lc_length)) 

    def __len__(self):
        return self.data_size
    
    def __getitem__(self, idx):
        
        return self.lc_torch[idx], self.lc_labels[idx]
    
def get_plasticc_datasets(path_to_plasticc, lazy_loading=True):
    
    if lazy_loading:
        print("You have selected lazy loading. Light curves will be loaded ondemand from the harddrive")
    else:
        print("You have selected eager loading. Light curves will be loaded on RAM, I hope you have enough")
    
    torch_datasets = []    
    # Load metadata
    p = Path(path_to_plasticc)
    df_meta = {}
    df_meta[False] = pd.read_csv(p / f'plasticc_train_metadata.csv').set_index("object_id")
    df_meta[True] = pd.read_csv(p / f'plasticc_test_metadata.csv').set_index("object_id")
    data_paths = sorted(p.glob('plasticc_*_lightcurves*.csv'))
    print(f"Found {len(data_paths)} csv files at given path")
    for data_path in data_paths:
        mode = 'test' in str(data_path)
        df_data = pd.read_csv(data_path).set_index("object_id")
        lc_ids = df_data.index.unique()            
        if lazy_loading:
            torch_datasets.append(PLAsTiCC_Torch_Dataset_Lazy(p / 'light_curves',
                                                              list(lc_ids), 
                                                              list(df_meta[mode]['true_target'].loc[lc_ids]), 
                                                              is_test=mode))
        else:
            print(f'Loading {data_path}')
            torch_datasets.append(PLAsTiCC_Torch_Dataset_Eager(df_data, 
                                                               list(lc_ids),
                                                               list(df_meta[mode]['true_target'].loc[lc_ids]),
                                                               is_test=mode))
                     

    
    return torch.utils.data.ConcatDataset(torch_datasets)
    
    