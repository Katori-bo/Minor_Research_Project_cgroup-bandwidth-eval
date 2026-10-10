/home/Aditya/Desktop/Research_project/cpu-quota-tail-latency/analysis/runtime_io_v16_repeatability_build/loadgen:     file format elf64-x86-64


Disassembly of section .text:

000000000048bf40 <time.now>:
  48bf40:	55                   	push   %rbp
  48bf41:	48 89 e5             	mov    %rsp,%rbp
  48bf44:	48 83 ec 10          	sub    $0x10,%rsp
  48bf48:	49 89 e4             	mov    %rsp,%r12
  48bf4b:	49 8b 5e 30          	mov    0x30(%r14),%rbx
  48bf4f:	48 8b 8b 88 03 00 00 	mov    0x388(%rbx),%rcx
  48bf56:	48 8b 93 80 03 00 00 	mov    0x380(%rbx),%rdx
  48bf5d:	48 89 0c 24          	mov    %rcx,(%rsp)
  48bf61:	48 89 54 24 08       	mov    %rdx,0x8(%rsp)
  48bf66:	48 8d 54 24 20       	lea    0x20(%rsp),%rdx
  48bf6b:	48 8b 4a f8          	mov    -0x8(%rdx),%rcx
  48bf6f:	48 89 8b 88 03 00 00 	mov    %rcx,0x388(%rbx)
  48bf76:	48 89 93 80 03 00 00 	mov    %rdx,0x380(%rbx)
  48bf7d:	4c 3b b3 b8 00 00 00 	cmp    0xb8(%rbx),%r14
  48bf84:	75 07                	jne    48bf8d <time.now+0x4d>
  48bf86:	48 8b 13             	mov    (%rbx),%rdx
  48bf89:	48 8b 62 38          	mov    0x38(%rdx),%rsp
  48bf8d:	48 83 ec 20          	sub    $0x20,%rsp
  48bf91:	48 83 e4 f0          	and    $0xfffffffffffffff0,%rsp
  48bf95:	bf 00 00 00 00       	mov    $0x0,%edi
  48bf9a:	48 8d 74 24 10       	lea    0x10(%rsp),%rsi
  48bf9f:	48 8b 05 2a 38 59 00 	mov    0x59382a(%rip),%rax        # a1f7d0 <runtime.vdsoClockgettimeSym>
  48bfa6:	48 83 f8 00          	cmp    $0x0,%rax
  48bfaa:	74 54                	je     48c000 <time.now+0xc0>
  48bfac:	ff d0                	call   *%rax
  48bfae:	bf 01 00 00 00       	mov    $0x1,%edi
  48bfb3:	48 8d 34 24          	lea    (%rsp),%rsi
  48bfb7:	48 8b 05 12 38 59 00 	mov    0x593812(%rip),%rax        # a1f7d0 <runtime.vdsoClockgettimeSym>
  48bfbe:	ff d0                	call   *%rax
  48bfc0:	48 8b 44 24 10       	mov    0x10(%rsp),%rax
  48bfc5:	48 8b 7c 24 18       	mov    0x18(%rsp),%rdi
  48bfca:	48 8b 0c 24          	mov    (%rsp),%rcx
  48bfce:	48 69 c9 00 ca 9a 3b 	imul   $0x3b9aca00,%rcx,%rcx
  48bfd5:	48 8b 54 24 08       	mov    0x8(%rsp),%rdx
  48bfda:	4c 89 e4             	mov    %r12,%rsp
  48bfdd:	48 8b 74 24 08       	mov    0x8(%rsp),%rsi
  48bfe2:	48 89 b3 80 03 00 00 	mov    %rsi,0x380(%rbx)
  48bfe9:	48 8b 34 24          	mov    (%rsp),%rsi
  48bfed:	48 89 b3 88 03 00 00 	mov    %rsi,0x388(%rbx)
  48bff4:	48 89 fb             	mov    %rdi,%rbx
  48bff7:	48 01 d1             	add    %rdx,%rcx
  48bffa:	48 83 c4 10          	add    $0x10,%rsp
  48bffe:	5d                   	pop    %rbp
  48bfff:	c3                   	ret
  48c000:	48 c7 c0 e4 00 00 00 	mov    $0xe4,%rax
  48c007:	0f 05                	syscall
  48c009:	bf 01 00 00 00       	mov    $0x1,%edi
  48c00e:	48 8d 34 24          	lea    (%rsp),%rsi
  48c012:	48 c7 c0 e4 00 00 00 	mov    $0xe4,%rax
  48c019:	0f 05                	syscall
  48c01b:	eb a3                	jmp    48bfc0 <time.now+0x80>
