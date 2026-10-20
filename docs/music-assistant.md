# Music Assistant setup

1. In Music Assistant: *Settings → Providers → Add provider → **Squeezelite / SlimProto*** (if not enabled yet).
2. Start the visualizer. A player named `player_name` ("Visualizer" by default) appears in MA within a few
   seconds. Its entity in Home Assistant is something like `media_player.visualizer`.
3. Play anything on it. With the blueprint (or by turning on `switch.music_visualizer`) the visuals appear on the
   Chromecast.

## Volume

Leave the player's volume in MA at **100 %**: it is the signal projectM reacts to. Control the real volume on
the TV or the Chromecast.

## Spotify app

Enable MA's **Spotify Connect** plugin for the visualizer player: it shows up in the Spotify app as a device
("Visualizer | Music Assistant"). Starting playback there starts everything.

## Voice

Because it is a normal MA player, Assist intents like "play <artist> on Visualizer" work as with any player.
