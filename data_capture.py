from screeps_utilities import create_api_connection_from_config
import os
import pickle

# data capture
def capture_snapshot(save_key):

    # config
    saved_snapshot_path = 'data/saved_snapshots.pickle'

    # load existing
    saved_snapshots = {}
    if os.path.exists(saved_snapshot_path):
        with open(saved_snapshot_path, 'rb') as handle:
            saved_snapshots = pickle.load(handle)

    # connect api
    api = create_api_connection_from_config('test_server.config')

    # get snapshot
    raw_memory_response = api.memory('', 'shard3')  # assuming json dictionary at this point
    raw_memory = raw_memory_response['data']
    saved_snapshots[save_key] = raw_memory

    # save snapshot
    with open(saved_snapshot_path, 'wb') as handle:
        pickle.dump(saved_snapshots, handle, protocol=pickle.HIGHEST_PROTOCOL)


if __name__ == '__main__':
    capture_snapshot('basic_start_test')