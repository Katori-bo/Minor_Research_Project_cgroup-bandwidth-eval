package main
import("encoding/hex";"testing")
func TestIndependentDigests(t *testing.T){
{v:=work(1);if hex.EncodeToString(v[:])!="630dcd2966c4336691125448bbb25b4ff412a49c732db2c8abc1b8581bd710dd"{t.Fatal("digest 1")}}
{v:=work(10);if hex.EncodeToString(v[:])!="ecb807a1906b5e5268b738f97d957a382e6e318fe30d404a46492494473761a0"{t.Fatal("digest 10")}}
{v:=work(44000);if hex.EncodeToString(v[:])!="6ce92f369a35e15408a64ba0300ad8f4ee2d2a49a11517f9e47de8325c70771c"{t.Fatal("digest 44000")}}
}
