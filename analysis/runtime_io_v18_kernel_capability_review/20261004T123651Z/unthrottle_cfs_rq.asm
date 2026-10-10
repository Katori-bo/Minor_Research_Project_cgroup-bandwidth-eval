
/usr/lib/modules/7.2.8-arch1-2/build/vmlinux:     file format elf64-x86-64


Disassembly of section .text:

ffffffff813dee30 <unthrottle_cfs_rq>:
ffffffff813dee30:	f3 0f 1e fa          	endbr64
ffffffff813dee34:	e8 67 48 f5 ff       	call   ffffffff813336a0 <__fentry__>
ffffffff813dee39:	48 83 ec 28          	sub    $0x28,%rsp
ffffffff813dee3d:	31 c0                	xor    %eax,%eax
ffffffff813dee3f:	48 89 1c 24          	mov    %rbx,(%rsp)
ffffffff813dee43:	48 89 fb             	mov    %rdi,%rbx
ffffffff813dee46:	48 89 6c 24 08       	mov    %rbp,0x8(%rsp)
ffffffff813dee4b:	48 8d af 00 02 00 00 	lea    0x200(%rdi),%rbp
ffffffff813dee52:	4c 89 64 24 10       	mov    %r12,0x10(%rsp)
ffffffff813dee57:	4c 89 6c 24 18       	mov    %r13,0x18(%rsp)
ffffffff813dee5c:	4c 8b af 58 01 00 00 	mov    0x158(%rdi),%r13
ffffffff813dee63:	4c 8b a7 38 01 00 00 	mov    0x138(%rdi),%r12
ffffffff813dee6a:	49 81 fd 00 1f 58 84 	cmp    $0xffffffff84581f00,%r13
ffffffff813dee71:	48 0f 44 e8          	cmove  %rax,%rbp
ffffffff813dee75:	e8 d6 a3 ff ff       	call   ffffffff813d9250 <update_curr>
ffffffff813dee7a:	8b 8b 64 01 00 00    	mov    0x164(%rbx),%ecx
ffffffff813dee80:	85 c9                	test   %ecx,%ecx
ffffffff813dee82:	74 0e                	je     ffffffff813dee92 <unthrottle_cfs_rq+0x62>
ffffffff813dee84:	48 83 bb 68 01 00 00 	cmpq   $0x0,0x168(%rbx)
ffffffff813dee8b:	00 
ffffffff813dee8c:	0f 8e dc 00 00 00    	jle    ffffffff813def6e <unthrottle_cfs_rq+0x13e>
ffffffff813dee92:	80 a3 a0 01 00 00 fe 	andb   $0xfe,0x1a0(%rbx)
ffffffff813dee99:	49 8d bd c0 01 00 00 	lea    0x1c0(%r13),%rdi
ffffffff813deea0:	e8 6b 87 1c 01       	call   ffffffff825a7610 <_raw_spin_lock>
ffffffff813deea5:	48 8b 83 b0 01 00 00 	mov    0x1b0(%rbx),%rax
ffffffff813deeac:	48 8b 93 a8 01 00 00 	mov    0x1a8(%rbx),%rdx
ffffffff813deeb3:	48 8d bb a8 01 00 00 	lea    0x1a8(%rbx),%rdi
ffffffff813deeba:	48 3b 38             	cmp    (%rax),%rdi
ffffffff813deebd:	0f 85 c2 d9 e2 ff    	jne    ffffffff8120c885 <unthrottle_cfs_rq.cold>
ffffffff813deec3:	48 3b 7a 08          	cmp    0x8(%rdx),%rdi
ffffffff813deec7:	0f 85 b8 d9 e2 ff    	jne    ffffffff8120c885 <unthrottle_cfs_rq.cold>
ffffffff813deecd:	48 89 42 08          	mov    %rax,0x8(%rdx)
ffffffff813deed1:	48 89 10             	mov    %rdx,(%rax)
ffffffff813deed4:	48 b8 22 01 00 00 00 	movabs $0xdead000000000122,%rax
ffffffff813deedb:	00 ad de 
ffffffff813deede:	48 89 83 b0 01 00 00 	mov    %rax,0x1b0(%rbx)
ffffffff813deee5:	48 8b 83 78 01 00 00 	mov    0x178(%rbx),%rax
ffffffff813deeec:	48 85 c0             	test   %rax,%rax
ffffffff813deeef:	0f 85 c0 00 00 00    	jne    ffffffff813defb5 <unthrottle_cfs_rq+0x185>
ffffffff813deef5:	49 8d bd c0 01 00 00 	lea    0x1c0(%r13),%rdi
ffffffff813deefc:	e8 1f 88 1c 01       	call   ffffffff825a7720 <_raw_spin_unlock>
ffffffff813def01:	48 8b bb 58 01 00 00 	mov    0x158(%rbx),%rdi
ffffffff813def08:	4c 89 e1             	mov    %r12,%rcx
ffffffff813def0b:	48 c7 c2 b0 ce 3d 81 	mov    $0xffffffff813dceb0,%rdx
ffffffff813def12:	48 c7 c6 e0 73 3c 81 	mov    $0xffffffff813c73e0,%rsi
ffffffff813def19:	e8 02 84 fe ff       	call   ffffffff813c7320 <walk_tg_tree_from>
ffffffff813def1e:	48 83 3b 00          	cmpq   $0x0,(%rbx)
ffffffff813def22:	75 28                	jne    ffffffff813def4c <unthrottle_cfs_rq+0x11c>
ffffffff813def24:	8b 93 40 01 00 00    	mov    0x140(%rbx),%edx
ffffffff813def2a:	85 d2                	test   %edx,%edx
ffffffff813def2c:	75 19                	jne    ffffffff813def47 <unthrottle_cfs_rq+0x117>
ffffffff813def2e:	eb 3e                	jmp    ffffffff813def6e <unthrottle_cfs_rq+0x13e>
ffffffff813def30:	48 8b bd b0 00 00 00 	mov    0xb0(%rbp),%rdi
ffffffff813def37:	e8 b4 43 ff ff       	call   ffffffff813d32f0 <list_add_leaf_cfs_rq>
ffffffff813def3c:	84 c0                	test   %al,%al
ffffffff813def3e:	75 0c                	jne    ffffffff813def4c <unthrottle_cfs_rq+0x11c>
ffffffff813def40:	48 8b ad a8 00 00 00 	mov    0xa8(%rbp),%rbp
ffffffff813def47:	48 85 ed             	test   %rbp,%rbp
ffffffff813def4a:	75 e4                	jne    ffffffff813def30 <unthrottle_cfs_rq+0x100>
ffffffff813def4c:	49 8d 84 24 f0 0d 00 	lea    0xdf0(%r12),%rax
ffffffff813def53:	00 
ffffffff813def54:	49 39 84 24 00 0e 00 	cmp    %rax,0xe00(%r12)
ffffffff813def5b:	00 
ffffffff813def5c:	0f 85 80 00 00 00    	jne    ffffffff813defe2 <unthrottle_cfs_rq+0x1b2>
ffffffff813def62:	49 8b 44 24 20       	mov    0x20(%r12),%rax
ffffffff813def67:	49 39 44 24 18       	cmp    %rax,0x18(%r12)
ffffffff813def6c:	74 1c                	je     ffffffff813def8a <unthrottle_cfs_rq+0x15a>
ffffffff813def6e:	48 8b 1c 24          	mov    (%rsp),%rbx
ffffffff813def72:	48 8b 6c 24 08       	mov    0x8(%rsp),%rbp
ffffffff813def77:	4c 8b 64 24 10       	mov    0x10(%rsp),%r12
ffffffff813def7c:	4c 8b 6c 24 18       	mov    0x18(%rsp),%r13
ffffffff813def81:	48 83 c4 28          	add    $0x28,%rsp
ffffffff813def85:	e9 26 a7 1c 01       	jmp    ffffffff825a96b0 <__pi___x86_return_thunk>
ffffffff813def8a:	41 8b 84 24 10 01 00 	mov    0x110(%r12),%eax
ffffffff813def91:	00 
ffffffff813def92:	85 c0                	test   %eax,%eax
ffffffff813def94:	74 d8                	je     ffffffff813def6e <unthrottle_cfs_rq+0x13e>
ffffffff813def96:	48 8b 1c 24          	mov    (%rsp),%rbx
ffffffff813def9a:	48 8b 6c 24 08       	mov    0x8(%rsp),%rbp
ffffffff813def9f:	4c 89 e7             	mov    %r12,%rdi
ffffffff813defa2:	4c 8b 6c 24 18       	mov    0x18(%rsp),%r13
ffffffff813defa7:	4c 8b 64 24 10       	mov    0x10(%rsp),%r12
ffffffff813defac:	48 83 c4 28          	add    $0x28,%rsp
ffffffff813defb0:	e9 9b 7e fe ff       	jmp    ffffffff813c6e50 <resched_curr>
ffffffff813defb5:	41 83 bc 24 a0 0e 00 	cmpl   $0x1,0xea0(%r12)
ffffffff813defbc:	00 01 
ffffffff813defbe:	76 29                	jbe    ffffffff813defe9 <unthrottle_cfs_rq+0x1b9>
ffffffff813defc0:	49 8b 94 24 90 0e 00 	mov    0xe90(%r12),%rdx
ffffffff813defc7:	00 
ffffffff813defc8:	48 29 c2             	sub    %rax,%rdx
ffffffff813defcb:	49 01 95 c0 02 00 00 	add    %rdx,0x2c0(%r13)
ffffffff813defd2:	48 c7 83 78 01 00 00 	movq   $0x0,0x178(%rbx)
ffffffff813defd9:	00 00 00 00 
ffffffff813defdd:	e9 13 ff ff ff       	jmp    ffffffff813deef5 <unthrottle_cfs_rq+0xc5>
ffffffff813defe2:	0f 0b                	ud2
ffffffff813defe4:	e9 79 ff ff ff       	jmp    ffffffff813def62 <unthrottle_cfs_rq+0x132>
ffffffff813defe9:	0f 0b                	ud2
ffffffff813defeb:	eb d3                	jmp    ffffffff813defc0 <unthrottle_cfs_rq+0x190>

Disassembly of section .data:

Disassembly of section .init.text:

Disassembly of section .altinstr_aux:

Disassembly of section .altinstr_replacement:

Disassembly of section .exit.text:
