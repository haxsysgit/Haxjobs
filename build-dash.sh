#!/bin/bash
cd /home/hermes/haxjobs/dashboard
npx vite build --outDir dist
echo 'Dashboard built and ready for restart: dashctl restart'
