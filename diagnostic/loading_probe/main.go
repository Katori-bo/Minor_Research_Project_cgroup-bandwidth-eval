// Startup executable provenance only; never runs during timed collection.
package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"syscall"
)

type identity struct {
	SHA256 string `json:"sha256"`
	Device uint64 `json:"device"`
	Inode uint64 `json:"inode"`
	Size int64 `json:"size"`
	Mode uint32 `json:"mode"`
	UID uint32 `json:"uid"`
	GID uint32 `json:"gid"`
}

func inspect(path string) (identity, error) {
	f, err := os.Open(path)
	if err != nil { return identity{}, err }
	defer f.Close()
	info, err := f.Stat()
	if err != nil { return identity{}, err }
	s, ok := info.Sys().(*syscall.Stat_t)
	if !ok || !info.Mode().IsRegular() { return identity{}, fmt.Errorf("not a regular Linux file: %s", path) }
	h := sha256.New()
	if _, err = io.Copy(h, f); err != nil { return identity{}, err }
	return identity{hex.EncodeToString(h.Sum(nil)), uint64(s.Dev), s.Ino, info.Size(), s.Mode, s.Uid, s.Gid}, nil
}

func main() {
	target, err := inspect("/proc/1/exe")
	if err != nil { fmt.Fprintln(os.Stderr, err); os.Exit(1) }
	self, err := inspect("/proc/self/exe")
	if err != nil { fmt.Fprintln(os.Stderr, err); os.Exit(1) }
	link, err := os.Readlink("/proc/1/exe")
	if err != nil { fmt.Fprintln(os.Stderr, err); os.Exit(1) }
	err = json.NewEncoder(os.Stdout).Encode(struct {
		Target identity `json:"target_executable"`
		Self identity `json:"probe_executable"`
		Link string `json:"target_link"`
	}{target, self, link})
	if err != nil { fmt.Fprintln(os.Stderr, err); os.Exit(1) }
}
