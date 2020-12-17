<!--- FIXME: Pick an emoji! --->
# 🌻 SkyHook

<!--- FIXME: Update crate, repo and CI workflow names here! Remove any that are not relevant --->
[![Embark](https://img.shields.io/badge/embark-open%20source-blueviolet.svg)](https://embark.dev)


## Engine and DCC communication system

SkyHook was created to facilitate communication between DCCs, standalone applications, web browsers and game engines. As of right now, it’s working in Houdini, Blender, Maya and Unreal Engine.

SkyHook works both with Python 2.7.x and 3.x and you don’t need to have the same Python version across programs. For example, you can build a standalone application in Python 3.8.5 and use SkyHook to communicate with Maya’s Python 2.7. This makes it much easier to use than something like RPyC where even a minor version difference can stop it from working.

SkyHook consist of 2 parts that can, but don’t have to, work together. There’s a client and a server. The server is just a very simple HTTP server that takes JSON requests. It parses those requests and tries to execute what was in them. The client just makes a a POST request to the server with a JSON payload. This is why you can basically use anything that’s able to do so as a client. Could be in a language other than Python, or even just webpage or mobile application.

## Pip installing

You should be able to pip install this package like this:
```batch
pip install git+https://github.com/EmbarkStudios/skyhook
```


## Contributing

[![Contributor Covenant](https://img.shields.io/badge/contributor%20covenant-v1.4-ff69b4.svg)](../main/CODE_OF_CONDUCT.md)

We welcome community contributions to this project.

Please read our [Contributor Guide](CONTRIBUTING.md) for more information on how to get started.

## License

Licensed under either of

* Apache License, Version 2.0, ([LICENSE-APACHE](LICENSE-APACHE) or http://www.apache.org/licenses/LICENSE-2.0)
* MIT license ([LICENSE-MIT](LICENSE-MIT) or http://opensource.org/licenses/MIT)

at your option.

### Contribution

Unless you explicitly state otherwise, any contribution intentionally submitted for inclusion in the work by you, as defined in the Apache-2.0 license, shall be dual licensed as above, without any additional terms or conditions.
