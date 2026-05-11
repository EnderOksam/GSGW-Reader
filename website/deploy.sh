#!/bin/bash
set -e
cd "$(dirname "$0")"
python ../scripts/build_web.py
npm run build
npx wrangler pages deploy .svelte-kit/cloudflare --project-name=gsgw
