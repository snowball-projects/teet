import time
import pyautogui
import pygetwindow as gw
import keyboard

WINDOW_TITLE_KEYWORD = "Warcraft"  # Change as needed
click = False
KEY_TO_PRESS = 'e'
INTERVAL = 1.1  # seconds between presses

def activate_game_window(title_keyword):
    windows = gw.getAllTitles()
    matches = [w for w in windows if title_keyword.lower() in w.lower()]
    if not matches:
        raise Exception(f"No window found with keyword '{title_keyword}'! Active windows: {windows}")
    game_window = gw.getWindowsWithTitle(matches[0])[0]
    game_window.activate()
    print(f"Activated window: {game_window.title}")

if __name__ == '__main__':
    print("Looking for your game window...")
    activate_game_window(WINDOW_TITLE_KEYWORD)
    print(f"Window activated. Will start pressing '{'Right Click' if click else KEY_TO_PRESS.upper()}' every {INTERVAL}s in 3 seconds...")
    print("Press ESC to stop.")

    time.sleep(3)
    try:
        while True:
            if keyboard.is_pressed('esc'):
                print("ESC pressed. Stopping script.")
                break
            if click:
                pyautogui.press('f1')
                pyautogui.press('f1')
                time.sleep(0.1)
                pyautogui.click(button='right')
            else:
                pyautogui.press(KEY_TO_PRESS)
            print(f"Pressed {'Right Click' if click else KEY_TO_PRESS.upper()}.")
            for _ in range(int(INTERVAL*10)):
                if keyboard.is_pressed('esc'):
                    print("ESC pressed. Stopping script.")
                    exit()
                time.sleep(0.1)
    except KeyboardInterrupt:
        print("Script stopped by user.")
