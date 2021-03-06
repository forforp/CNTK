
# Copyright (c) Microsoft. All rights reserved.

# Licensed under the MIT license. See LICENSE.md file in the project root
# for full license information.
# ==============================================================================

import os
import numpy as np

abs_path = os.path.dirname(os.path.abspath(__file__))

def test_text_format():
    from cntk.io import text_format_minibatch_source, StreamConfiguration, MinibatchSource

    # 0	|x 560	|y 1 0 0 0 0
    # 0	|x 0
    # 0	|x 0
    # 1	|x 560	|y 0 1 0 0 0
    # 1	|x 0
    # 1	|x 0
    # 1	|x 424
    path = os.path.join(abs_path, 'tf_data.txt')

    input_dim = 1000
    num_output_classes = 5

    mb_source = text_format_minibatch_source(path, [
                    StreamConfiguration( 'features', input_dim, True, 'x' ),
                    StreamConfiguration( 'labels', num_output_classes, False, 'y')], 0)
    assert isinstance(mb_source, MinibatchSource)

    features_si = mb_source.stream_info('features')
    labels_si = mb_source.stream_info('labels')

    mb = mb_source.get_next_minibatch(7)

    features = mb[features_si].m_data
    # 2 samples, max seq len 4, 1000 dim
    assert features.data().shape().dimensions() == (2, 4, input_dim)
    assert features.data().is_sparse()
    # TODO features is sparse and cannot be accessed right now:
    # *** RuntimeError: DataBuffer/WritableDataBuffer methods can only be called for NDArrayiew objects with dense storage format

    labels = mb[labels_si].m_data
    # 2 samples, max seq len 1, 5 dim
    assert labels.data().shape().dimensions() == (2, 1, num_output_classes)
    assert not labels.data().is_sparse()

    assert np.allclose(np.asarray(labels),
            np.asarray([
                [[ 1.,  0.,  0.,  0.,  0.]],
                [[ 0.,  1.,  0.,  0.,  0.]]
                ]))

def test_image():
    from cntk.io import ReaderConfig, ImageDeserializer
    map_file = "input.txt"
    mean_file = "mean.txt"
    epoch_size = 150

    feature_name = "f"
    image_width = 100
    image_height = 200
    num_channels = 3

    label_name = "l"
    num_classes = 7
    
    image = ImageDeserializer(map_file)
    image.map_features(feature_name,
            [ImageDeserializer.crop(crop_type='Random', ratio=0.8,
                jitter_type='uniRatio'),
             ImageDeserializer.scale(width=image_width, height=image_height,
                 channels=num_channels, interpolations='linear'),
             ImageDeserializer.mean(mean_file)])
    image.map_labels(label_name, num_classes)

    rc = ReaderConfig(image, randomize=False, epoch_size=epoch_size)

    assert rc['epochSize'] == epoch_size
    assert rc['randomize'] == False
    assert len(rc['deserializers']) == 1
    d = rc['deserializers'][0]
    assert d['type'] == 'ImageDeserializer'
    assert d['file'] == map_file
    assert set(d['input'].keys()) == {label_name, feature_name}

    l = d['input'][label_name]
    assert l['labelDim'] == num_classes

    f = d['input'][feature_name]
    assert set(f.keys()) == { 'transforms' }
    t0, t1, t2 = f['transforms']
    assert t0['type'] == 'Crop'
    assert t1['type'] == 'Scale'
    assert t2['type'] == 'Mean'
    t0['cropType'] == 'Random'
    t0['cropRatio'] == 0.8
    t0['jitterType'] == 'uniRatio'
    t1['width'] == image_width
    t1['height'] == image_height
    t1['channels'] == num_channels
    t1['interpolations'] == 'linear'
    t2['type'] == 'mean'
    t2['meanFile'] == mean_file

    # TODO depends on ImageReader.dll
    ''' 
    mbs = rc.minibatch_source()
    sis = mbs.stream_infos()
    assert set(sis.keys()) == { feature_name, label_name }
    '''

def test_minibatch(tmpdir):

    mbdata = r'''0	|S0 0   |S1 0
0	|S0 1 	|S1 1 
0	|S0 2 	
0	|S0 3 	|S1 3 
1	|S0 4 	
1	|S0 5 	|S1 1
1	|S0 6	|S1 2 
'''

    tmpfile = str(tmpdir/'mbtest.txt')
    with open(tmpfile, 'w') as f:
        f.write(mbdata)

    feature_stream_name = 'features'
    labels_stream_name = 'labels'

    from cntk.io import text_format_minibatch_source, StreamConfiguration
    mb_source = text_format_minibatch_source(tmpfile, [
        StreamConfiguration(feature_stream_name, 1, False, 'S0'),
        StreamConfiguration(labels_stream_name, 1, False, 'S1')],
        randomize=False)

    features_si = mb_source.stream_info(feature_stream_name)
    labels_si = mb_source.stream_info(labels_stream_name)
    
    mb = mb_source.next_minibatch(1000)
    assert mb[features_si].num_sequences == 2
    assert mb[labels_si].num_sequences == 2

    features = mb[features_si]
    assert len(features.value) == 2
    expected_features = \
            [
                [[0],[1],[2],[3]],
                [[4],[5],[6]]
            ]

    for res, exp in zip (features.value, expected_features):
        assert np.allclose(res, exp)

    assert np.allclose(features.mask, 
            [[2, 1, 1, 1],
             [2, 1, 1, 0]])

    labels = mb[labels_si]
    assert len(labels.value) == 2
    expected_labels = \
            [
                [[0],[1],[3]], 
                [[1],[2]]
            ]
    for res, exp in zip (labels.value, expected_labels):
        assert np.allclose(res, exp)

    assert np.allclose(labels.mask, 
            [[2, 1, 1],
             [2, 1, 0]])
