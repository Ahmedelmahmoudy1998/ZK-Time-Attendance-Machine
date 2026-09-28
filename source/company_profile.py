"""Company identity stored with each attendance database, including its logo."""
from io import BytesIO
import warnings

MAX_LOGO_BYTES = 5 * 1024 * 1024


def normalize_logo(data):
    if not data:
        return b''
    if not isinstance(data, bytes) or len(data) > MAX_LOGO_BYTES:
        raise ValueError('Choose a PNG or JPEG logo no larger than 5 MB.')
    from PIL import Image, ImageOps
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as image:
                if image.format not in ('PNG', 'JPEG') or image.width * image.height > 16000000:
                    raise ValueError('Unsupported logo.')
                image = ImageOps.exif_transpose(image).convert('RGBA')
                image.thumbnail((600, 240), Image.Resampling.LANCZOS)
                out = BytesIO()
                image.save(out, format='PNG')
                return out.getvalue()
    except (OSError, ValueError, Image.DecompressionBombWarning, Image.DecompressionBombError) as ex:
        raise ValueError('Choose a valid PNG or JPEG logo (up to 16 million pixels).') from ex


class CompanyProfileStore:
    def company_profile(self):
        row = self.db.execute('SELECT company_name, branch, logo FROM company_profile WHERE id=1').fetchone()
        return dict(row) if row else {'company_name': '', 'branch': '', 'logo': b''}

    def save_company_profile(self, company_name, branch, logo=b''):
        self.require('admin')
        values = [company_name.strip(), branch.strip()]
        if any(len(value) > 160 or any(ord(c) < 32 for c in value) for value in values):
            raise ValueError('Company and branch must each be one line of up to 160 characters.')
        logo = normalize_logo(logo)
        with self.db:
            self.db.execute('''INSERT INTO company_profile(id,company_name,branch,logo)
                VALUES(1,?,?,?) ON CONFLICT(id) DO UPDATE SET
                company_name=excluded.company_name,branch=excluded.branch,logo=excluded.logo''', (*values, logo))
            self.log('Company name, branch and logo updated')
