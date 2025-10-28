package fs_watcher

import (
	"fmt"
	"os"
)

func ensureDirExists(p string) error {
	info, err := os.Stat(p)
	if err != nil {
		if os.IsNotExist(err) {
			return fmt.Errorf("directory not exist: %s", p)
		}
		return fmt.Errorf("stat %s: %w", p, err)
	}
	if !info.IsDir() {
		return fmt.Errorf("path is not a directory: %s", p)
	}
	return nil
}

func isDir(p string) bool {
	stat, err := os.Stat(p)
	return err == nil && stat.IsDir()
}
