import qrcode
from PIL import Image, ImageDraw
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.colormasks import SolidFillColorMask
from qrcode.image.styles.moduledrawers import RoundedModuleDrawer


def create_styled_qr(
    data,
    logo_path,
    output_file,
    qr_color=(0, 51, 153),  # синий
    bg_color=(255, 255, 255),
    logo_bg_ratio=0.28,
    logo_ratio=0.70,
    corner_radius_ratio=0.18,
):
    """
    Красивый QR с:
    - закруглёнными модулями
    - логотипом по центру
    - белой подложкой под логотип
    """

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=16,
        border=3,
    )

    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(
        image_factory=StyledPilImage,
        module_drawer=RoundedModuleDrawer(),
        color_mask=SolidFillColorMask(front_color=qr_color, back_color=bg_color),
    )

    img = img.convert("RGBA")

    qr_width, qr_height = img.size

    # ---------------------------------------------------
    # Белая подложка под логотип
    # ---------------------------------------------------

    bg_size = int(qr_width * logo_bg_ratio)
    radius = int(bg_size * corner_radius_ratio)

    logo_bg = Image.new("RGBA", (bg_size, bg_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(logo_bg)

    draw.rounded_rectangle((0, 0, bg_size, bg_size), radius=radius, fill=(255, 255, 255, 255))

    bg_x = (qr_width - bg_size) // 2
    bg_y = (qr_height - bg_size) // 2

    img.paste(logo_bg, (bg_x, bg_y), logo_bg)

    # ---------------------------------------------------
    # Логотип
    # ---------------------------------------------------

    logo = Image.open(logo_path)

    if logo.mode != "RGBA":
        logo = logo.convert("RGBA")

    logo_size = int(bg_size * logo_ratio)

    logo.thumbnail((logo_size, logo_size), Image.Resampling.LANCZOS)

    logo_x = (qr_width - logo.width) // 2
    logo_y = (qr_height - logo.height) // 2

    img.paste(logo, (logo_x, logo_y), logo)

    img.save(output_file)
    print(f"QR сохранён: {output_file}")


if __name__ == "__main__":
    create_styled_qr(
        data="https://www.maz.by",
        logo_path=r"D:\Documents\client\logo_maz.png",
        output_file=r"D:\Documents\client\maz_qr_styled.png",
        qr_color=(0, 73, 180),  # фирменный синий
        bg_color=(255, 255, 255),
        logo_bg_ratio=0.30,
        logo_ratio=0.75,
    )
