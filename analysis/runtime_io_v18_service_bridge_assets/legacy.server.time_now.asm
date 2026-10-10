/home/Aditya/Desktop/Research_project/cpu-quota-tail-latency/analysis/runtime_io_v16_repeatability_build/binary_audit/legacy.server:     file format elf64-x86-64


Disassembly of section .text:

000000000048be00 <time.now>:
  48be00:	55                   	push   %rbp
  48be01:	48 89 e5             	mov    %rsp,%rbp
  48be04:	48 83 ec 10          	sub    $0x10,%rsp
  48be08:	49 89 e4             	mov    %rsp,%r12
  48be0b:	49 8b 5e 30          	mov    0x30(%r14),%rbx
  48be0f:	48 8b 8b 88 03 00 00 	mov    0x388(%rbx),%rcx
  48be16:	48 8b 93 80 03 00 00 	mov    0x380(%rbx),%rdx
  48be1d:	48 89 0c 24          	mov    %rcx,(%rsp)
  48be21:	48 89 54 24 08       	mov    %rdx,0x8(%rsp)
  48be26:	48 8d 54 24 20       	lea    0x20(%rsp),%rdx
  48be2b:	48 8b 4a f8          	mov    -0x8(%rdx),%rcx
  48be2f:	48 89 8b 88 03 00 00 	mov    %rcx,0x388(%rbx)
  48be36:	48 89 93 80 03 00 00 	mov    %rdx,0x380(%rbx)
  48be3d:	4c 3b b3 b8 00 00 00 	cmp    0xb8(%rbx),%r14
  48be44:	75 07                	jne    48be4d <time.now+0x4d>
  48be46:	48 8b 13             	mov    (%rbx),%rdx
  48be49:	48 8b 62 38          	mov    0x38(%rdx),%rsp
  48be4d:	48 83 ec 20          	sub    $0x20,%rsp
  48be51:	48 83 e4 f0          	and    $0xfffffffffffffff0,%rsp
  48be55:	bf 00 00 00 00       	mov    $0x0,%edi
  48be5a:	48 8d 74 24 10       	lea    0x10(%rsp),%rsi
  48be5f:	48 8b 05 fa 59 56 00 	mov    0x5659fa(%rip),%rax        # 9f1860 <runtime.vdsoClockgettimeSym>
  48be66:	48 83 f8 00          	cmp    $0x0,%rax
  48be6a:	74 54                	je     48bec0 <time.now+0xc0>
  48be6c:	ff d0                	call   *%rax
  48be6e:	bf 01 00 00 00       	mov    $0x1,%edi
  48be73:	48 8d 34 24          	lea    (%rsp),%rsi
  48be77:	48 8b 05 e2 59 56 00 	mov    0x5659e2(%rip),%rax        # 9f1860 <runtime.vdsoClockgettimeSym>
  48be7e:	ff d0                	call   *%rax
  48be80:	48 8b 44 24 10       	mov    0x10(%rsp),%rax
  48be85:	48 8b 7c 24 18       	mov    0x18(%rsp),%rdi
  48be8a:	48 8b 0c 24          	mov    (%rsp),%rcx
  48be8e:	48 69 c9 00 ca 9a 3b 	imul   $0x3b9aca00,%rcx,%rcx
  48be95:	48 8b 54 24 08       	mov    0x8(%rsp),%rdx
  48be9a:	4c 89 e4             	mov    %r12,%rsp
  48be9d:	48 8b 74 24 08       	mov    0x8(%rsp),%rsi
  48bea2:	48 89 b3 80 03 00 00 	mov    %rsi,0x380(%rbx)
  48bea9:	48 8b 34 24          	mov    (%rsp),%rsi
  48bead:	48 89 b3 88 03 00 00 	mov    %rsi,0x388(%rbx)
  48beb4:	48 89 fb             	mov    %rdi,%rbx
  48beb7:	48 01 d1             	add    %rdx,%rcx
  48beba:	48 83 c4 10          	add    $0x10,%rsp
  48bebe:	5d                   	pop    %rbp
  48bebf:	c3                   	ret
  48bec0:	48 c7 c0 e4 00 00 00 	mov    $0xe4,%rax
  48bec7:	0f 05                	syscall
  48bec9:	bf 01 00 00 00       	mov    $0x1,%edi
  48bece:	48 8d 34 24          	lea    (%rsp),%rsi
  48bed2:	48 c7 c0 e4 00 00 00 	mov    $0xe4,%rax
  48bed9:	0f 05                	syscall
  48bedb:	eb a3                	jmp    48be80 <time.now+0x80>
