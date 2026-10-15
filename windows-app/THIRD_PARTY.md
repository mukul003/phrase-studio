# Third-party components

The source application uses ASP.NET Core/.NET (Microsoft, MIT), Python (Python Software Foundation license), Pillow (HPND/Pillow license), FFmpeg and FFprobe. The portable build is assembled by PyInstaller (GPL with its exception for bundled applications). Windows system fonts are loaded from the user's own Windows installation, not redistributed.

FFmpeg is installed by the Chocolatey `ffmpeg` package during the build. Its configured components and license vary with that package. The build records `ffmpeg -version` and `ffmpeg -L` alongside the binaries. Consult the included license notices and vendor source/build links before redistributing a generated package:

- .NET: https://github.com/dotnet/runtime
- Python: https://www.python.org/psf/license/
- Pillow: https://github.com/python-pillow/Pillow
- PyInstaller: https://pyinstaller.org/en/stable/license.html
- FFmpeg source and licenses: https://ffmpeg.org/download.html and https://ffmpeg.org/legal.html
- Windows FFmpeg vendor/build sources: https://www.gyan.dev/ffmpeg/builds/
- Chocolatey package provenance: https://community.chocolatey.org/packages/ffmpeg

No credentials, recorded audio or user data are included in build artifacts.
