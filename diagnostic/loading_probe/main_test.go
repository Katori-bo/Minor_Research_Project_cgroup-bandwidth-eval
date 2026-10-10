package main

import (
	"os"
	"path/filepath"
	"testing"
)

func TestIdentityRetainsHashAndSameFile(t *testing.T) {
	p := filepath.Join(t.TempDir(), "file")
	if err := os.WriteFile(p, []byte("abc"), 0755); err != nil { t.Fatal(err) }
	a, err := inspect(p)
	if err != nil { t.Fatal(err) }
	b, err := inspect(p)
	if err != nil || a != b { t.Fatalf("unstable identity: %+v %+v %v", a, b, err) }
	if a.SHA256 != "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad" || a.Size != 3 || a.Inode == 0 { t.Fatalf("bad identity: %+v", a) }
	if _, err := inspect(filepath.Dir(p)); err == nil { t.Fatal("directory accepted") }
	if _, err := inspect(p + ".missing"); err == nil { t.Fatal("missing file accepted") }
}

func TestActualSelfExecutable(t *testing.T) {
	x, err := inspect("/proc/self/exe")
	if err != nil || len(x.SHA256) != 64 || x.Size <= 0 { t.Fatalf("self: %+v %v", x, err) }
}
