# sources/

Authoritative originals: survey DWG files, deed and plot documents (سند،
پلاک ثبتی), municipal conditions (دستور نقشه / طرح تفصیلی), geotechnical
reports. **Never modify, rename or re-save anything here.** Convert into
`derived/` with `bin/hp dwg2dxf`.

When a file arrives, record its checksum:

```sh
shasum -a 256 sources/<file> >> sources/MANIFEST.sha256
shasum -a 256 -c sources/MANIFEST.sha256   # verify nothing changed
```

Large or private originals may be kept out of git; the manifest still is.
