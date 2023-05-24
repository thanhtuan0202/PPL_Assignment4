.source MT22Class.java
.class public MT22Class
.super java.lang.Object
.field static c I
	iconst_1
	putstatic MT22Class.c I

.method public static main([Ljava/lang/String;)V
.var 0 is args [Ljava/lang/String; from Label0 to Label1
Label0:
.var 1 is b I from Label0 to Label1
	iconst_4
	istore_1
	iconst_2
	anewarray int
	astore_2
	aload_2
	iconst_0
	iconst_3
	newarray int
	aastore
	aload_2
	iconst_0
	iconst_3
	newarray int
	aastore
	iconst_1
	iconst_3
	newarray int
	aastore
	iload_2
	iconst_1
	iconst_2
	iconst_2
	iastore
Label1:
	return
.limit stack 11
.limit locals 3
.end method
