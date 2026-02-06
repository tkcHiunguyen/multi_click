# VM Multi Cursor (MVP)

MVP Windows tool to mirror mouse + keyboard input from the primary screen to multiple VMware Workstation Pro windows.

## Quick start

1. Install Python 3.10+.
2. Install deps:
   
   ```powershell
   python -m pip install -r requirements.txt
   ```
3. Run:
   
   ```powershell
   python src/app.py
   ```

## Notes
- UI is Vietnamese.
- This MVP uses window message injection (PostMessage). Some apps may not fully honor injected messages.
- VMware windows should be fixed position/size after you save anchors.
