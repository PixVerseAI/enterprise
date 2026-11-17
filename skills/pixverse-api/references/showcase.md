# PixVerse Showcase

Browse original example videos, input assets, prompts, and recorded settings. Videos and the music preview play directly on GitHub; images use PixVerse CDN URLs. Original media URLs are retained in [showcase data](showcase.json).

## Choose an example

| No. | Example | CLI | MCP |
|---|---|---|---|
| SC-01 | <a href="#sc-01-desert-road-at-sunset">Desert road at sunset</a> | `video generate` | `video_generate` |
| SC-02 | <a href="#sc-02-lakeside-camping-coffee">Lakeside camping coffee</a> | `video from-image` | `video_from_image` |
| SC-03 | <a href="#sc-03-flower-shop-from-day-to-night">Flower shop from day to night</a> | `video f2v` | `video_f2v` |
| SC-04 | <a href="#sc-04-mountain-hiking-with-three-references">Mountain hiking with three references</a> | `video fusion` | `video_fusion` |
| SC-05 | <a href="#sc-05-continue-shaping-a-pottery-cup">Continue shaping a pottery cup</a> | `video extend` | `video_extend` |
| SC-06 | <a href="#sc-06-widen-a-lighthouse-coastline">Widen a lighthouse coastline</a> | `video expand` | `video_expand` |
| SC-07 | <a href="#sc-07-turn-street-dance-into-hand-drawn-animation">Turn street dance into hand-drawn animation</a> | `video restyle` | `video_restyle` |
| SC-08 | <a href="#sc-08-improve-the-animation-resolution">Improve the animation resolution</a> | `video upscale` | `video_upscale` |
| SC-09 | <a href="#sc-09-add-gentle-rain-sounds">Add gentle rain sounds</a> | `video sound-effect` | `video_sound_effect` |
| SC-10 | <a href="#sc-10-city-street-from-morning-to-night">City street from morning to night</a> | `video multi-transition` | `video_multi_transition` |
| SC-11 | <a href="#sc-11-remove-a-floor-lamp">Remove a floor lamp</a> | `video modify` | `video_modify` |
| SC-12 | <a href="#sc-12-animate-a-character-with-a-dance-reference">Animate a character with a dance reference</a> | `video mimic` | `video_mimic` |
| SC-13 | <a href="#sc-13-a-short-lifestyle-message">A short lifestyle message</a> | `video lipsync` | `video_lipsync` |
| SC-14 | <a href="#sc-14-a-welcoming-brand-introduction">A welcoming brand introduction</a> | `video avatar` | `video_avatar` |
| SC-15 | <a href="#sc-15-replace-a-corridor-character">Replace a corridor character</a> | `video swap` | `video_swap` |
| SC-16 | <a href="#sc-16-midnight-haunts-music-video">Midnight Haunts music video</a> | `agent mv` | `agent_mv` |
| SC-17 | <a href="#sc-17-a-presenter-introduces-a-crossbody-bag">A presenter introduces a crossbody bag</a> | `agent ecommerce-native` | `agent_ecommerce_native` |
| SC-18 | <a href="#sc-18-a-crossbody-bag-ad-without-a-visible-presenter">A crossbody bag ad without a visible presenter</a> | `agent ecommerce-template` | `agent_ecommerce_template` |

## Recreate an example

- Read only the selected example. Complete recorded settings are available in [showcase data](showcase.json), under its case ID.
- Download the linked input assets and upload them to the active account. Use the new IDs returned by that connection. Historical account-bound IDs and webhook IDs are omitted.
- Recorded settings use historical Platform field names and are not ready-to-submit MCP arguments. Map them through the connected tool's input schema or the installed CLI's `--help`; preserve explicit `false`, zero, reference names, and input order.
- Obtain a current voice for TTS. For Swap, run Mask Selection again and pair its returned keyframe/mask IDs with the same uploaded source video. The displayed mask is a visual reference.
- Known request fields are preserved; missing historical fields are not invented. Original files, prompts, settings, and output videos are retained. A new run may differ, even with the same seed.
- Viewing examples does not authorize generation. Submit only within the user's requested scope and budget, and retain accepted task IDs when querying results.

## Examples

## SC-01 Desert road at sunset

CLI: `pixverse-api video generate` · MCP: `video_generate`

### Inputs

Text only; no input media.

### Original prompt

> A single continuous cinematic wide shot of one vintage off-road vehicle driving steadily along a winding desert road at sunset. The vehicle remains on the road with realistic wheel contact, distant dunes stay stable, a modest trail of dust follows behind. Smooth tracking camera, natural golden light. No cuts, no other vehicles or people, no text or logos.

### Recorded settings

```json
{
  "negative_prompt": "",
  "model": "v6-max",
  "aspect_ratio": "16:9",
  "quality": "720p",
  "duration": 8,
  "motion_mode": "normal",
  "seed": 661002,
  "water_mark": false,
  "generate_audio_switch": false
}
```

### Original example video

https://github.com/user-attachments/assets/b3691e2e-10b8-405c-8b42-ac06ae758a4f

## SC-02 Lakeside camping coffee

CLI: `pixverse-api video from-image` · MCP: `video_from_image`

### Inputs

![Camp image](https://media.pixverse.ai/openapi%2Fdb61b438-68d5-4740-a409-61c4a48e0c5e_747fd35610f63e434951214e17b21177_auto.png)

### Original prompt

> Animate this exact lakeside camp photo in one continuous locked camera shot. The same seated camper slowly tilts the same metal coffee pot and pours a thin coherent stream into the same mug on the table, then returns the pot upright. Preserve the hands, mug handle, tent, lake and mountains, realistic gravity, no sudden object changes, no extra people, no text.

### Recorded settings

```json
{
  "negative_prompt": "",
  "model": "v6-max",
  "quality": "720p",
  "duration": 8,
  "motion_mode": "normal",
  "seed": 661004,
  "water_mark": false,
  "generate_audio_switch": false
}
```

### Original example video

https://github.com/user-attachments/assets/520867da-94eb-415d-a80f-4fa796b70ea2

## SC-03 Flower shop from day to night

CLI: `pixverse-api video f2v` · MCP: `video_f2v`

### Inputs

![First frame](https://media.pixverse.ai/openapi%2F8184b180-1982-4959-8bf2-e1b9668105ae_69ff311e7e4434e235b82c3188352583_auto.png)

![Last frame](https://media.pixverse.ai/openapi%2Fc95566eb-33d8-4899-b494-7853702e0b9b_e9053a0618d0cb2e05bc4814df754409_auto.png)

### Original prompt

> One seamless locked-off shot of the same flower shop. Daylight gradually fades through dusk into blue-hour night while the existing shop interior lights and wall lanterns gently illuminate, arriving precisely at the final frame. Keep door, windows, plants, flowers, awning, architecture and camera composition stable. No people, no cuts, no text.

### Recorded settings

```json
{
  "negative_prompt": "",
  "model": "v6",
  "quality": "720p",
  "duration": 8,
  "motion_mode": "normal",
  "seed": 661007,
  "water_mark": false,
  "generate_audio_switch": false,
  "play_bgm": false
}
```

### Original example video

https://github.com/user-attachments/assets/dd295117-d037-4883-9eab-58d886f1bcb9

## SC-04 Mountain hiking with three references

CLI: `pixverse-api video fusion` · MCP: `video_fusion`

### Inputs

![Person reference: person](https://media.pixverse.ai/openapi%2F0f159618-0097-421b-aaed-29592ceb050d_17fa6bd96bc37909ec2b1d15b592de61_auto.png)

![Jacket reference: item](https://media.pixverse.ai/openapi%2F45956e7e-015a-4957-8aa5-279f1c8eaa1d_7b01f4de536ea2f2ff2127e55588c48d_auto.png)

![Location reference: place](https://media.pixverse.ai/openapi%2Fd1b1acd6-f407-468b-aa99-82fe4decbaab_494ee7d153c9b61818af5c119a892762_auto.png)

### Original prompt

> At @place , @person wears @item and walks slowly along the gravel path near the wooden railing, then gently turns toward the camera. Preserve his face, curly hair, body shape, the burnt-orange jacket with charcoal zippers, and the distant mountain landscape. Stable realistic footing and natural movement, one continuous shot, no other people, no logos or text.

### Recorded settings

```json
{
  "negative_prompt": "",
  "model": "v6",
  "quality": "720p",
  "duration": 8,
  "seed": 661011,
  "water_mark": false,
  "generate_audio_switch": false,
  "image_references": [
    {
      "ref_name": "person"
    },
    {
      "ref_name": "item"
    },
    {
      "ref_name": "place"
    }
  ],
  "aspect_ratio": "16:9"
}
```

### Original example video

https://github.com/user-attachments/assets/5fa1626a-dc35-4a7c-87eb-223ee15c7b78

## SC-05 Continue shaping a pottery cup

CLI: `pixverse-api video extend` · MCP: `video_extend`

### Inputs

https://github.com/user-attachments/assets/d01a64d3-9f72-41e0-ba76-4594af5d333e

### Original prompt

> Continue the same uninterrupted close shot for five seconds. The same potter gently refines the same one clay cup on the same spinning wheel. Both hands maintain physically plausible contact; the continuous circular rim slowly becomes smooth and even. Preserve one cup, correct fingers, wheel rotation direction, body, studio, lighting and camera position throughout. Natural slow movements, no cuts or added objects.

### Recorded settings

```json
{
  "model": "v6",
  "duration": 5,
  "quality": "720p",
  "motion_mode": "normal",
  "generate_audio_switch": false,
  "water_mark": false,
  "seed": 631102,
  "negative_prompt": "extra fingers, fused hands, floating hands, broken cup, extra cups, warped rim, reversed wheel, jump cut, text, logos"
}
```

### Original example video

https://github.com/user-attachments/assets/93917274-02ea-43d2-b9c5-58de327aadcb

## SC-06 Widen a lighthouse coastline

CLI: `pixverse-api video expand` · MCP: `video_expand`

### Inputs

https://github.com/user-attachments/assets/1003b4da-0a15-4f0c-9eae-0bed23c851b3

No generation prompt was supplied in the recorded request.

### Recorded settings

```json
{
  "quality": "720p",
  "aspect_ratio": "16:9"
}
```

- No prompt or seed was supplied in the recorded request.

### Original example video

https://github.com/user-attachments/assets/bcf2daed-b29e-4872-a7b8-7395c9d8ba02

## SC-07 Turn street dance into hand-drawn animation

CLI: `pixverse-api video restyle` · MCP: `video_restyle`

### Inputs

https://github.com/user-attachments/assets/bf6111d7-f0d9-446b-9b56-756ad98cccf2

### Original prompt

> A vivid hand-drawn 2D anime animation, bold black ink outlines, cel-shaded illustrated face and clothing, flat graphic colors and a painted cartoon background. The whole scene is fully illustrated frame by frame.

### Recorded settings

```json
{
  "seed": 610604,
  "negative_prompt": "photorealism, realistic photograph, live action, blurry, flicker, text, logo"
}
```

### Original example video

https://github.com/user-attachments/assets/9c423403-da08-40a5-8695-444934f9d170

## SC-08 Improve the animation resolution

CLI: `pixverse-api video upscale` · MCP: `video_upscale`

### Inputs

https://github.com/user-attachments/assets/9c423403-da08-40a5-8695-444934f9d170

No generation prompt was supplied in the recorded request.

### Recorded settings

```json
{
  "seed": 731201
}
```

- This is the original API upscale result, not the locally downscaled 720p derivative.

### Original example video

https://github.com/user-attachments/assets/ffeb68fe-134e-4fd3-99c7-fdac4c92d219

## SC-09 Add gentle rain sounds

CLI: `pixverse-api video sound-effect` · MCP: `video_sound_effect`

### Inputs

https://github.com/user-attachments/assets/f6a87eb7-d08f-4628-96e8-6ebc96824a98

### Original prompt

> Natural rainfall pattering softly against the window glass and outside on wet ground, gentle rain ambience and a faint breeze in the garden. Continuous realistic sound, no thunder, speech or music.

### Recorded settings

```json
{
  "original_sound_switch": false,
  "seed": 631202,
  "water_mark": false
}
```

### Original example video

https://github.com/user-attachments/assets/f5b6e4b9-5720-4ac9-a3b9-ac64ca653537

## SC-10 City street from morning to night

CLI: `pixverse-api video multi-transition` · MCP: `video_multi_transition`

### Inputs

![Morning frame](https://media.pixverse.ai/openapi%2Fd6a0814f-52d8-4697-a326-4cac1149a76c_0c9389e7336d79557fabbfc0b5131dd2_auto.png)

![Sunset frame](https://media.pixverse.ai/openapi%2F1be347e7-4fe1-431a-a62d-f07b01d1f34e_01241b4d76e78e4e4a0c8a94bf473627_auto.png)

![Night frame](https://media.pixverse.ai/openapi%2F413057cb-8855-45e5-8a29-193f33c8f39c_5fd0cd0a6cd405ff9cf53dcc702c5f08_auto.png)

### Original prompt

> Smooth cinematic time lapse of the same city street corner transitioning naturally from morning to golden sunset and then blue hour night. Keep the architecture, street layout and camera angle consistent while the sky and lights gradually change. No cuts, no people, no cars, no text.

### Recorded settings

```json
{
  "model": "v5",
  "quality": "720p",
  "motion_mode": "normal",
  "seed": 631401,
  "water_mark": false
}
```

Frame prompts and per-segment durations are retained in [showcase data](showcase.json).

- The two starting frames each request five seconds; the final frame omits duration. The measured output is shorter than the requested segment total.

### Original example video

https://github.com/user-attachments/assets/5b56f846-3fa5-4c1a-9b3a-b37d015b89e9

## SC-11 Remove a floor lamp

CLI: `pixverse-api video modify` · MCP: `video_modify`

### Inputs

https://github.com/user-attachments/assets/df24b8aa-c3dc-49cb-98b4-fa3f118c0462

### Original prompt

> Remove the freestanding floor lamp with the cream shade on the right side of the room throughout the video. Fill the area naturally with the existing plain wall, baseboard and wooden floor. Keep the woman, her walking motion, sofa, table, plants, room lighting and static camera unchanged. Do not remove any other object or add objects, text or logos.

### Recorded settings

```json
{
  "quality": "720p",
  "water_mark": false,
  "seed": 12345
}
```

- The original request used no reference image or mask.

### Original example video

https://github.com/user-attachments/assets/6d42014e-8ac7-4dfe-8947-6d4d4fb1f9b4

## SC-12 Animate a character with a dance reference

CLI: `pixverse-api video mimic` · MCP: `video_mimic`

### Inputs

![Target character](https://media.pixverse.ai/openapi%2F0825d910-3ae6-4f48-a871-0c92f069f806_46ed42e912199da640160b154340d39b_auto.png)

https://github.com/user-attachments/assets/bf6111d7-f0d9-446b-9b56-756ad98cccf2

No generation prompt was supplied in the recorded request.

### Recorded settings

```json
{
  "quality": "720p",
  "water_mark": false
}
```

- No prompt was used. The original optional request fields were not fully retained; a response seed is not treated as an explicit request seed.

### Original example video

https://github.com/user-attachments/assets/bc15204f-31b2-42f0-9198-427e997f10f9

## SC-13 A short lifestyle message

CLI: `pixverse-api video lipsync` · MCP: `video_lipsync`

### Inputs

https://github.com/user-attachments/assets/8a223b71-7b4e-4be3-ab78-590f0c0e1596

### Original speech text

> A gentle morning routine can make the whole day feel different. Open the curtains, take a deep breath, and leave a little time for something you love.

### Recorded settings

```json
{
  "water_mark": false
}
```

- The original voice was Lyan. Query a currently available voice instead of copying its historical numeric ID.

### Original example video

https://github.com/user-attachments/assets/e3b27969-e6b7-4621-b7df-45da9bc8983e

## SC-14 A welcoming brand introduction

CLI: `pixverse-api video avatar` · MCP: `video_avatar`

### Inputs

![Presenter image](https://media.pixverse.ai/openapi%2F97428e1f-8bb7-4796-adc0-52b502630d28_eb4efbb4ec17f473072afd67e124734e_auto.png)

### Original prompt

> The presenter looks into the camera and speaks naturally with a welcoming expression, gentle small nods, natural blinks and restrained gestures; keep her face unobstructed and preserve the original person, clothing and background.

### Recorded settings

```json
{
  "water_mark": false
}
```

The original Chinese speech text is retained verbatim in [showcase data](showcase.json).

- The original demo uses Chinese TTS and the historical Jessica Anne Bogart voice. Query a suitable voice on the active connection; the original full request was not retained.

### Original example video

https://github.com/user-attachments/assets/8fc6c4ce-0b21-4983-a17c-4cb38c5cbb7c

## SC-15 Replace a corridor character

CLI: `pixverse-api video swap` · MCP: `video_swap`

### Inputs

https://github.com/user-attachments/assets/a7914f49-2069-4a85-a4dd-32124c0c13e8

![Replacement character](https://media.pixverse.ai/openapi%2Fdac6d26d-023b-41b8-97e8-387c10918137_72f4a17fd5d2e87c014727dd535570b9_auto.png)

![Historical mask preview](https://media.pixverse.ai/openapi%2F707a0935-683e-4fcb-a349-fc2d805926db_f7b8f400dd1270edce434f329fe0b9c0_auto.png)

No generation prompt was supplied in the recorded request.

### Recorded settings

```json
{
  "quality": "720p",
  "seed": 631303,
  "water_mark": false
}
```

- The mask image is a historical visual reference only. Run Mask Selection on the same newly uploaded source video and use its actual returned keyframe and mask IDs.

### Original example video

https://github.com/user-attachments/assets/cd4b2546-4065-414d-b10e-7d776a135901

## SC-16 Midnight Haunts music video

CLI: `pixverse-api agent mv` · MCP: `agent_mv`

### Inputs

![Character reference](https://media.pixverse.ai/openapi%2Fc40a2ad3-97c6-4077-aa49-9545a1576105_5c06cd2cbbeb139efcb7ff5ab24e0068_auto.png)

Music reference preview (unmute to listen). For reproduction, use the original MP3 in [showcase data](showcase.json).

https://github.com/user-attachments/assets/e177583c-8aab-4087-a229-5831800f1d89

### Original prompt

> A playful spooky Halloween music video featuring the reference character and a moonlit ghost parade.

### Recorded settings

```json
{
  "mv_agent_type": "vibe_mv_v3_custom",
  "mv_style": "Midnight Haunts",
  "music_style": "",
  "lip_sync_switch": true,
  "preserve_outfit": true,
  "caption_switch": false,
  "instrumental_switch": false,
  "quality": "720p",
  "aspect_ratio": "9:16",
  "seed": 20261030,
  "water_mark": false
}
```

- V3 Custom music video. Audio verification is asynchronous; no separate verification tool is required. Style availability is validated by Platform.

### Original example video

https://github.com/user-attachments/assets/9f17f892-a36b-463f-ac31-33c1721986ef

## SC-17 A presenter introduces a crossbody bag

CLI: `pixverse-api agent ecommerce-native` · MCP: `agent_ecommerce_native`

### Inputs

![Product image](https://media.pixverse.ai/openapi%2F123d96e0-3699-4ce1-aad3-dabe4c75dac1_f4b175fa5baeda26a5b75c96d812fa77_auto.png)

![Presenter image](https://media.pixverse.ai/openapi%2F405629b4-2fbe-4899-9e5d-f32d8e2f13c1_a91291bd391b8f757ab95e5019cfa8b4_auto.png)

### Original prompt

> Create a 15-second contemporary fashion advertisement featuring the supplied female presenter and the exact cognac-brown leather crossbody bag from the product image. Start with the presenter introducing the bag in a naturally lit apartment, cut to clear close-ups of its curved flap, stitching and brass clasp, then show her wearing the same bag across her body as she walks outdoors. End with a composed hero shot of the bag. Keep the presenter's face and clothing consistent and preserve the bag's shape, color, single strap and hardware across shots. Use elegant camera movement, believable handling, concise natural English narration and readable English captions. Do not invent brands, prices, logos or unsupported material claims.

### Recorded settings

```json
{
  "agent_id": 414562414124107,
  "duration": 15,
  "quality": "720p",
  "aspect_ratio": "16:9",
  "language_code": "en-US",
  "lip_sync_switch": true,
  "bgm_switch": true,
  "caption_switch": true,
  "img_references": [
    {
      "ref_name": "product"
    }
  ]
}
```

- Use the presenter image for the avatar input and the bag image for the product reference.
- No seed, watermark, video references, or webhook was supplied in the recorded request.

### Original example video

https://github.com/user-attachments/assets/47bb9ddc-65b8-42a8-9041-de08d8042087

## SC-18 A crossbody bag ad without a visible presenter

CLI: `pixverse-api agent ecommerce-template` · MCP: `agent_ecommerce_template`

### Inputs

![Product image](https://media.pixverse.ai/openapi%2F123d96e0-3699-4ce1-aad3-dabe4c75dac1_f4b175fa5baeda26a5b75c96d812fa77_auto.png)

### Original prompt

> Create a 15-second contemporary fashion advertisement for the exact cognac-brown leather crossbody bag in the product image. Present the bag without any visible face or identifiable person; hands or cropped body may demonstrate it, with off-camera narration. Use a naturally lit apartment, clear close-ups of the curved flap, stitching and brass clasp, and a lifestyle view showing the bag worn across the body. End with a composed hero shot. Preserve the bag's shape, color, single strap and hardware across shots. Use elegant camera movement, believable handling, concise natural English narration and readable English captions. Do not invent brands, prices, logos or unsupported material claims.

### Recorded settings

```json
{
  "agent_id": 414562414124108,
  "duration": 15,
  "quality": "720p",
  "aspect_ratio": "16:9",
  "language_code": "en-US",
  "lip_sync_switch": true,
  "bgm_switch": true,
  "caption_switch": true,
  "img_references": [
    {
      "ref_name": "product"
    }
  ],
  "video_style": "no_personal_review"
}
```

- No seed, watermark, video references, or webhook was supplied in the recorded request.

### Original example video

https://github.com/user-attachments/assets/70fd5f68-8af3-4071-ab93-d19a03726e83

## Video templates

The original collection has no video-template example. Discover available templates and their required inputs before proposing a template case. No example video is claimed here.
