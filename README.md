## Another attempt to add a better support for Nuki devices to the Home Assistant

### Features:
* Lock interface implementation
* Uses local webhook from bridge to receive real-time updates
* Exposes all available information from bridge via sensors
* Optionally, if web API and token is enabled, exposes authorization objects (keypad codes, accounts) as entities

### Installation:
* Checkout/clone the contents of this repo to `~.homeassistant/custom_components/nuki_ng/`
* Restart your Home Assistant
* Add new integration (search for `Nuki Lock` in the list)
* Input bridge API token (mandatory) and web API token (optional, if you have it enabled)

### Screenshots:
<img width="1020" alt="Screenshot 2021-10-11 at 14 02 42" src="https://user-images.githubusercontent.com/159124/136786951-d1ffdb22-637a-49c2-a1ff-43c465a03f0b.png">
