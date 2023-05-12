# Copyright (c) OpenMMLab. All rights reserved.
import warnings

import torch
import torch.nn.functional as F
from ..builder import DETECTORS
from .detr import DETR
from ..roi_heads.deformdetr_cls_head import CLS_Head
from .single_stage import SingleStageDetector

@DETECTORS.register_module()
class DeformableDETR_TCT(DETR):

    def __init__(self, *args, **kwargs):
        super(DETR, self).__init__(*args, **kwargs)
        
        self.cls_head = None
        cls_head=dict(
            in_channels=256,
            in_index=0,
            loss_weight=0.3,
            pos_list=[1, 2, 3, 4, 5]
        )
        self.cls_head = CLS_Head(
            in_channels=cls_head['in_channels'],
            in_index=cls_head['in_index'],
            loss_weight=cls_head['loss_weight'],
            pos_list=cls_head['pos_list'],
        )
            
    
    def get_decoder_out(self,mlvl_feats, img_metas):
        batch_size = mlvl_feats[0].size(0)
        input_img_h, input_img_w = img_metas[0]['batch_input_shape']
        img_masks = mlvl_feats[0].new_ones(
            (batch_size, input_img_h, input_img_w))
        for img_id in range(batch_size):
            img_h, img_w, _ = img_metas[img_id]['img_shape']
            img_masks[img_id, :img_h, :img_w] = 0

        mlvl_masks = []
        mlvl_positional_encodings = []
        for feat in mlvl_feats:
            mlvl_masks.append(
                F.interpolate(img_masks[None],
                              size=feat.shape[-2:]).to(torch.bool).squeeze(0))
            mlvl_positional_encodings.append(
                self.bbox_head.positional_encoding(mlvl_masks[-1]))

        query_embeds = None
        if not self.bbox_head.as_two_stage:
            query_embeds = self.bbox_head.query_embedding.weight
        hs, init_reference, inter_references, \
            enc_outputs_class, enc_outputs_coord = self.bbox_head.transformer(
                    mlvl_feats,
                    mlvl_masks,
                    query_embeds,
                    mlvl_positional_encodings,
                    reg_branches=self.bbox_head.reg_branches if self.bbox_head.with_box_refine else None,  # noqa:E501
                    cls_branches=self.bbox_head.cls_branches if self.bbox_head.as_two_stage else None  # noqa:E501
            )
        return hs
    
    
    
    
    
    def forward_train(self,
                      img,
                      img_metas,
                      gt_bboxes,
                      gt_labels,
                      gt_bboxes_ignore=None):
        # BaseDetector
        batch_input_shape = tuple(img[0].size()[-2:])
        for img_meta in img_metas:
            img_meta['batch_input_shape'] = batch_input_shape

        # SingleStageDetector

        x = self.extract_feat(img)
        losses = self.bbox_head.forward_train(x, img_metas, gt_bboxes,
                                              gt_labels, gt_bboxes_ignore)

        # NEW
        # need to get decoder output
        decoder_querys = self.get_decoder_out(x,img_metas)[-1] #get the last layer decoder output
        decoder_querys = decoder_querys.permute(1,2,0)
        
        #print(decoder_querys.size())  torch.size([1,256,300]) 即 [B,dim,num_query]
        
        if self.cls_head is not None:
            cls_binary_losses = self.cls_head.forward_train(decoder_querys, gt_labels)
            losses.update(cls_binary_losses)
        # END NEW
        return losses
