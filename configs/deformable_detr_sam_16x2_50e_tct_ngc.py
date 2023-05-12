num_classes = 6


model = dict(
    type='DeformableDETR',
    backbone=dict(
        type='ImageEncoderViT',
        depth=32,#12 24 32
        embed_dim=1280,#768 1024 1280
        img_size=1024,
        mlp_ratio=4,
        num_heads=16,#12 16 16
        patch_size=16,
        qkv_bias=True,
        use_rel_pos=True,
        global_attn_indexes=[7, 15, 23, 31] ,#[2,5,8,11] [5,11,17,23] [7, 15, 23, 31] 
        window_size=14,
        out_chans=256,
        pretrained='SAM-H'#SAM-B SAM-L SAM-H
        ),
    neck=dict(
        type='SimpleFeaturePyramidMapper',
        in_channels=256,
        out_channels=256,
        scale_factors=(4.0, 2.0, 1.0, 0.5),),
    bbox_head=dict(
        type='DeformableDETRHead',
        num_query=300,
        num_classes=num_classes,
        in_channels=2048, #这个参数对于DeformableDETRHead没用，对于DETRHead才有作用
        sync_cls_avg_factor=True,
        as_two_stage=False,
        transformer=dict(
            type='DeformableDetrTransformer',
            encoder=dict(
                type='DetrTransformerEncoder',
                num_layers=6,
                transformerlayers=dict(
                    type='BaseTransformerLayer',
                    attn_cfgs=dict(
                        type='MultiScaleDeformableAttention', embed_dims=256),
                    feedforward_channels=1024,
                    ffn_dropout=0.1,
                    operation_order=('self_attn', 'norm', 'ffn', 'norm'))),
            decoder=dict(
                type='DeformableDetrTransformerDecoder',
                num_layers=6,
                return_intermediate=True,
                transformerlayers=dict(
                    type='DetrTransformerDecoderLayer',
                    attn_cfgs=[
                        dict(
                            type='MultiheadAttention',
                            embed_dims=256,
                            num_heads=8,
                            dropout=0.1),
                        dict(
                            type='MultiScaleDeformableAttention',
                            embed_dims=256)
                    ],
                    feedforward_channels=1024,
                    ffn_dropout=0.1,
                    operation_order=('self_attn', 'norm', 'cross_attn', 'norm',
                                     'ffn', 'norm')))),
        positional_encoding=dict(
            type='SinePositionalEncoding',
            num_feats=128,
            normalize=True,
            offset=-0.5),
        loss_cls=dict(
            type='FocalLoss',
            use_sigmoid=True,
            gamma=2.0,
            alpha=0.25,
            loss_weight=2.0),
        loss_bbox=dict(type='L1Loss', loss_weight=5.0),
        loss_iou=dict(type='GIoULoss', loss_weight=2.0)),
    train_cfg=dict(
        assigner=dict(
            type='HungarianAssigner',
            cls_cost=dict(type='FocalLossCost', weight=2.0),
            reg_cost=dict(type='BBoxL1Cost', weight=5.0, box_format='xywh'),
            iou_cost=dict(type='IoUCost', iou_mode='giou', weight=2.0))),
    test_cfg=dict(max_per_img=100))
img_norm_cfg = dict(
    mean=[123.675, 116.28, 103.53], std=[58.395, 57.12, 57.375], to_rgb=True)
train_pipeline = [
    dict(type='LoadImageFromFile'),
    dict(type='LoadAnnotations', with_bbox=True),
    dict(type='RandomFlip', flip_ratio=0.5),
    dict(
        type='AutoAugment',
        policies=[[{
            'type':
            'Resize',
            'img_scale': [(480, 1333), (512, 1333), (544, 1333), (576, 1333),
                          (608, 1333), (640, 1333), (672, 1333), (704, 1333),
                          (736, 1333), (768, 1333), (800, 1333)],
            'multiscale_mode':
            'value',
            'keep_ratio':
            True
        }],
                  [{
                      'type': 'Resize',
                      'img_scale': [(400, 4200), (500, 4200), (600, 4200)],
                      'multiscale_mode': 'value',
                      'keep_ratio': True
                  }, {
                      'type': 'RandomCrop',
                      'crop_type': 'absolute_range',
                      'crop_size': (384, 600),
                      'allow_negative_crop': True
                  }, {
                      'type':
                      'Resize',
                      'img_scale': [(480, 1333), (512, 1333), (544, 1333),
                                    (576, 1333), (608, 1333), (640, 1333),
                                    (672, 1333), (704, 1333), (736, 1333),
                                    (768, 1333), (800, 1333)],
                      'multiscale_mode':
                      'value',
                      'override':
                      True,
                      'keep_ratio':
                      True
                  }]]),
    # dict(
    #     type='Normalize',
    #     mean=[123.675, 116.28, 103.53],
    #     std=[58.395, 57.12, 57.375],
    #     to_rgb=True),
    dict(
        type='Albu',
        transforms=[
            dict(
            type='ShiftScaleRotate',
            shift_limit=0.0625,
            scale_limit=0.0,
            rotate_limit=180,
            interpolation=1,
            p=0.5),

            dict(
            type='OneOf',
            transforms=[
                dict(
                    type='RGBShift',
                    r_shift_limit=10,
                    g_shift_limit=10,
                    b_shift_limit=10,
                    p=0.5),
                dict(
                    type='HueSaturationValue',
                    hue_shift_limit=20,
                    sat_shift_limit=30,
                    val_shift_limit=20,
                    p=0.5)
            ],
            p=0.5),
            
            dict(
            type='OneOf',
            transforms=[
                dict(type='Blur', blur_limit=3, p=0.7),
                dict(type='MedianBlur', blur_limit=3, p=0.5)
            ],
            p=0.1),

        ],
        bbox_params=dict(
            type='BboxParams',
            format='pascal_voc',
            label_fields=['gt_labels'],
            min_visibility=0.0,
            filter_lost_elements=True),
        keymap={
            'img': 'image',
            'gt_masks': 'masks',
            'gt_bboxes': 'bboxes'
        },
    ),
    dict(type='SelfNormalize'),
    dict(type='Pad', size_divisor=1),
    dict(type='DefaultFormatBundle'),
    dict(type='Collect', keys=['img', 'gt_bboxes', 'gt_labels'])
]
test_pipeline = [
    dict(type='LoadImageFromFile'),
    dict(
        type='MultiScaleFlipAug',
        img_scale=(1333, 800),
        flip=False,
        transforms=[
            dict(type='Resize', keep_ratio=True),
            dict(type='RandomFlip'),
            # dict(
            #     type='Normalize',
            #     mean=[123.675, 116.28, 103.53],
            #     std=[58.395, 57.12, 57.375],
            #     to_rgb=True),
            dict(type='SelfNormalize'),
            dict(type='Pad', size_divisor=1),
            dict(type='ImageToTensor', keys=['img']),
            dict(type='Collect', keys=['img'])
        ])
]
data = dict(
    samples_per_gpu=1,
    workers_per_gpu=1,
    train=dict(
        type='tctDataset',
        ann_file='/home/commonfile/tct_ngc_data/annotations/train.json',
        img_prefix='/home/commonfile/TCTAnnotated(non-gynecologic)/',
        filter_empty_gt=False,
        pipeline=train_pipeline),
    val=dict(
        type='tctDataset',
        ann_file='/home/commonfile/tct_ngc_data/annotations/val.json',
        img_prefix='/home/commonfile/TCTAnnotated(non-gynecologic)/',
        pipeline=test_pipeline),
    test=dict(
        type='tctDataset',
        ann_file='/home/commonfile/tct_ngc_data/annotations/test.json',
        img_prefix='/home/commonfile/TCTAnnotated(non-gynecologic)/',
        pipeline=test_pipeline))

optimizer = dict(
    type='AdamW',
    lr=0.0002,
    weight_decay=0.0001,
    paramwise_cfg=dict(
        custom_keys=dict(
            backbone=dict(lr_mult=0.1),
            sampling_offsets=dict(lr_mult=0.1),
            reference_points=dict(lr_mult=0.1))))
optimizer_config = dict(grad_clip=dict(max_norm=0.1, norm_type=2))
lr_config = dict(policy='step', step=[40])
runner = dict(type='EpochBasedRunner', max_epochs=50)
work_dir = 'work_dirs/deformable_detr_tct_ngc_393/bysmear/sam_b_backbone'


evaluation = dict(interval=5, metric='bbox')
checkpoint_config = dict(interval=5)
log_config = dict(interval=50, hooks=[dict(type='TextLoggerHook')])
custom_hooks = [dict(type='NumClassCheckHook')]
dist_params = dict(backend='nccl')
log_level = 'INFO'
#load_from = '/home/ligaojie/mmdetection_2.18.0/deformable_detr_r50_16x2_50e_coco_20210419_220030-a12b9512.pth'
resume_from = None
load_from = None
workflow = [('train', 1)]