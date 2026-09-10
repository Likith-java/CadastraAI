import torch
import torch.nn as nn
import segmentation_models_pytorch as smp

class FrameFieldUnetDeep(nn.Module):
    def __init__(self, encoder_name="resnet34", in_channels=3):
        super().__init__()
        base = smp.Unet(encoder_name=encoder_name, encoder_weights=None,
                         in_channels=in_channels, classes=1)
        self.encoder = base.encoder
        self.decoder = base.decoder
        decoder_out_channels = base.segmentation_head[0].in_channels

        self.mask_head = nn.Conv2d(decoder_out_channels, 1, kernel_size=3, padding=1)
        self.edge_head = nn.Sequential(
            nn.Conv2d(decoder_out_channels, 32, kernel_size=3, padding=1), nn.ReLU(inplace=True),
            nn.Conv2d(32, 1, kernel_size=3, padding=1)
        )
        self.frame_field_head = nn.Sequential(
            nn.Conv2d(decoder_out_channels, 32, kernel_size=3, padding=1), nn.ReLU(inplace=True),
            nn.Conv2d(32, 2, kernel_size=3, padding=1)
        )

    def forward(self, x):
        features = self.encoder(x)
        decoder_output = self.decoder(features)
        return {
            "mask": self.mask_head(decoder_output),
            "frame_field": self.frame_field_head(decoder_output),
            "edge": self.edge_head(decoder_output),
        }

def load_model(checkpoint_path, device="cpu"):
    model = FrameFieldUnetDeep()
    state_dict = torch.load(checkpoint_path, map_location=device)
    model.load_state_dict(state_dict)
    model.to(device).eval()
    return model
