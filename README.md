**Status**: alpha, work in progress

# About

This is the implementation for the i18n support for AngularJS 1.4+ and Angular2.  It's meant to be generic enough so as not to be too tied to Angular though the initial versions will be focussed entirely on Angular.

# References
The primary reference document is [Angular and Internationalization: The New World][] published under published under [Angular Public][]/[Design Docs][]/[i18n][].

The document [v1.0][] focusses on work for first release.

# Quick Start

```zsh
# Checkout the source
git clone git@github.com:angular/i18n.git
cd i18n

# Install pre-requisites.
# This will ask you for sudo permissions.
./setup
```

## Run a sample extraction

```zsh
# NOTE:  This uses a hardcoded path and extract from
#     demo/index.html and prints the results onto the console and not to
#     a file on disk.
./tools/extract_messages
```

## Run a sample pseudo translation

```zsh
# NOTE:  This reads from demo/index.html and (over)writes demo/index-zz.html.
./tools/pseudo_translate
```

<!-- Named Links -->

[Angular and Internationalization: The New World]: https://drive.google.com/open?id=1mwyOFsAD-bPoXTk3Hthq0CAcGXCUw-BtTJMR4nGTY-0
[Angular Public]: https://drive.google.com/folderview?id=0BxgtL8yFJbacQmpCc1NMV3d5dnM
[Design Docs]: https://drive.google.com/folderview?id=0BxgtL8yFJbacQmpCc1NMV3d5dnM
[i18n]: https://drive.google.com/folderview?id=0BxgtL8yFJbacQmpCc1NMV3d5dnM
[v1.0]: https://drive.google.com/open?id=1-pLAhklbR7CMLkY4pYgwjoDCLyNlNGVnO_lDZiuN9KA
