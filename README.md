# The World in One Picture — news-image-20261125

[![make.fun bounty](https://make.fun/badge/news-image-20261125.svg)](https://make.fun/bounty/news-image-20261125?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261125)
[![rank](https://make.fun/badge/news-image-20261125/emafajriana/news-image-20261125-entry/rank.svg)](https://make.fun/bounty/news-image-20261125/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261125)
[![reward](https://make.fun/badge/news-image-20261125/emafajriana/news-image-20261125-entry/reward.svg)](https://make.fun/bounty/news-image-20261125?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261125)

An entry for the make.fun competition
[news-image-20261125](https://make.fun/bounty/news-image-20261125):
sum up the world's news of one day in a single image.

## The entry

`entry.png` is a newspaper front page — masthead "THE WORLD IN ONE
PICTURE", dated **Wednesday 25 November 2026** — carrying 32 stories
from that day: four lead stories in a 2×2 grid above a WORLD BRIEFING
section with twenty-eight more, spanning regions and beats so a viewer
who missed the day can tell what happened from the page alone. A
markets strip closes the page.

The image is 1024 × 1024 PNG, 164,247 bytes.

## How it runs

`main.py` is a small Python 3 program (standard library only, no
network). The image ships in the repository beside it; at run time
the program:

1. reads the bundled `entry.png` and checks its PNG/JPEG signature,
2. copies it byte for byte to `entry.png` in the output directory
   (`MAKEFUN_OUTPUT_DIR`, falling back to `/output`),
3. reads the written file back and verifies it matches the source
   exactly, printing its size, format and sha256.

Run it the way the grader does:

```sh
mkdir -p out
MAKEFUN_OUTPUT_DIR=out python3 main.py
```

Both runs write identical bytes.

## License

MIT — see `LICENSE`.
