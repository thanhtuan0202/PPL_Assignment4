from Emitter import Emitter
from functools import reduce

from Frame import Frame
from abc import ABC
from Visitor import *
from AST import *



class MType:
    def __init__(self, partype, rettype):
        self.partype = partype
        self.rettype = rettype


class Symbol:
    def __init__(self, name, mtype, value=None):
        self.name = name
        self.mtype = mtype
        self.value = value

    def __str__(self):
        return "Symbol(" + self.name + "," + str(self.mtype) + ")"


class CodeGenerator:
    def __init__(self):
        self.libName = "io"

    def init(self):
        return [Symbol("readInteger", MType(list(), IntegerType()), CName(self.libName)),
                Symbol("printInteger", MType([IntegerType()],
                       VoidType()), CName(self.libName))
                ]

    def gen(self, ast, path):
        # ast: AST
        # dir_: String

        gl = self.init()
        gc = CodeGenVisitor(ast, gl, path)
        gc.visit(ast, None)


class SubBody():
    def __init__(self, frame, sym,isGlobal = False):
        self.frame = frame
        self.sym = sym

class Access():
    def __init__(self, frame, sym, isLeft, isFirst=False):
        self.frame = frame
        self.sym = sym
        self.isLeft = isLeft
        self.isFirst = isFirst


class Val(ABC):
    pass


class Index(Val):
    def __init__(self, value):
        self.value = value


class CName(Val):
    def __init__(self, value):
        self.value = value


class CodeGenVisitor(Visitor):
    def __init__(self, astTree, env, path):
        self.astTree = astTree
        self.env = env
        self.path = path
        self.className = "MT22Class"
        self.emit = Emitter(self.path + "/" + self.className + ".j")
        
        self.listGlobalArray = [] # list(VarDecl: array declare global)
    def visitProgram(self, ast, c):
        self.emit.printout(self.emit.emitPROLOG(self.className, "java.lang.Object"))
        
        staticDecl = self.env
        for x in ast.decls:
            if type(x) is FuncDecl:
                partype = [i.varType for i in x.params]
                staticDecl = [Symbol(x.name.lower(), MType(partype, x.return_type), CName(self.className))] + staticDecl
            else:
                newSym = self.visit(x, SubBody(None, None, isGlobal=True))
                staticDecl = [newSym] + staticDecl
        c = SubBody(None, staticDecl)
        [self.visit(x, c) for x in ast.decls if type(x) is FuncDecl]
    
    def visitClassDecl(self, ast, c):
        self.className = ast.classname.name
        self.emit = Emitter(self.path+"/" + self.className + ".j")
        self.emit.printout(self.emit.emitPROLOG(
            self.className, "java.lang.Object"))
        [self.visit(ele, SubBody(None, self.env))
         for ele in ast.memlist if type(ele) == MethodDecl]
        # generate default constructor
        self.genMETHOD(MethodDecl(Instance(), Id("<init>"), list(
        ), None, Block([], [])), c, Frame("<init>", VoidType()))
        self.emit.emitEPILOG()
        return c

    def genMETHOD(self, consdecl, o, frame):
        isInit = consdecl.return_type is None
        isMain = consdecl.name == "main" and len(
            consdecl.params) == 0 and type(consdecl.return_type) is VoidType
        return_type = VoidType() if isInit else consdecl.return_type
        methodName = "<init>" if isInit else consdecl.name
        intype = [ArrayType(0, StringType())] if isMain else list(
            map(lambda x: x.typ, consdecl.params))
        mtype = MType(intype, return_type)

        self.emit.printout(self.emit.emitMETHOD(
            methodName, mtype, not isInit, frame))

        frame.enterScope(True)

        glenv = o

        # Generate code for parameter declarations
        if isInit:
            self.emit.printout(self.emit.emitVAR(frame.getNewIndex(), "this", ClassType(
                Id(self.className)), frame.getStartLabel(), frame.getEndLabel(), frame))
        elif isMain:
            self.emit.printout(self.emit.emitVAR(frame.getNewIndex(), "args", ArrayType(
                0, StringType()), frame.getStartLabel(), frame.getEndLabel(), frame))
        else:
            local = reduce(lambda env, ele: SubBody(frame, [self.visit(ele, env)]+env.sym), consdecl.params, SubBody(frame, []))
            glenv = local.sym+glenv

        body = consdecl.body
        self.emit.printout(self.emit.emitLABEL(frame.getStartLabel(), frame))

        # Generate code for statements
        if isInit:
            self.emit.printout(self.emit.emitREADVAR(
                "this", ClassType(Id(self.className)), 0, frame))
            self.emit.printout(self.emit.emitINVOKESPECIAL(frame))
            
        list(map(lambda x: self.visit(x, SubBody(frame, glenv)), body.body))

        self.emit.printout(self.emit.emitLABEL(frame.getEndLabel(), frame))
        if type(return_type) is VoidType:
            self.emit.printout(self.emit.emitRETURN(VoidType(), frame))
        self.emit.printout(self.emit.emitENDMETHOD(frame))
        frame.exitScope()

    def visitFuncDecl(self, ast, o):
        frame = Frame(ast.name, ast.return_type)
        self.genMETHOD(ast, o.sym, frame)
        return Symbol(ast.name, MType([x.typ for x in ast.params], ast.return_type), CName(self.className))
    
    def visitVarDecl(self,ast,o):
        subctxt = o
        frame = o.frame
        varName = ast.name
        varType = ast.typ
        #global variable
        if o.frame is None:
            self.emit.printout(self.emit.emitATTRIBUTE(varName, varType, False, ast.init if ast.init is not None else ""))
            if type(ast.typ) is ArrayType: 
                self.listGlobalArray.append(ast)
            return Symbol(varName, varType, CName(self.className))
        # params or local variables
        idx = frame.getNewIndex()
        self.emit.printout(self.emit.emitVAR(idx, varName, varType, frame.getStartLabel(), frame.getEndLabel(), frame))
        return SubBody(frame, [Symbol(varName, varType, Index(idx))] + subctxt.sym)   


################---visit statements---######################     
    def visitAssign(self, ast, o): 
        ctx = o
        if type(ast.lhs) is ArrayCell:
            [frame.push() for i in range(0,2)]
        lc,lt = self.visit(ast.lhs,Access(ctx.frame,ctx.sym,True,False))
        rc,rt = self.visit(ast.rhs,Access(ctx.frame,ctx.sym,False,False))
        if type(lt) is FloatType and type(rt) is IntegerType:
            rc = rc + self.emit.emitI2F(ctx.frame)
        if type(ast.lhs) is ArrayCell:
            self.emit.printout(lc[0] + rc + lc[1])
            # recover stack status
            [frame.pop() for i in range(0,2)]  
        else: 
            self.emit.printout(rc + lc)          
    
    def visitIf(self, ast, o): 
        newo = o
        if ast.fstmt is None:
            ec,et = self.visit(ast.cond,Access(newo.frame,newo.sym,False,False))
            self.emit.printout(ec)
            #get new label
            FLABEL = newo.frame.getNewLabel()
            code = self.emit.emitIFFALSE(FLABEL,newo.frame) # jump to FLABEL if expr return false, ignore true stmt
            self.emit.printout(code)
            #visit true stmt
            self.visit(ast.tstmt,newo)
            #position of FLABEL
            code = self.emit.emitLABEL(FLABEL,newo.frame)
            self.emit.printout(code)           
        else:    
            ec,et = self.visit(ast.cond,Access(newo.frame,newo.sym,False,False))
            self.emit.printout(ec)
            #get new label
            FLABEL = newo.frame.getNewLabel()
            code = self.emit.emitIFFALSE(FLABEL,newo.frame) # jump to FLabel if expr return false
            self.emit.printout(code)
            #visit true stmt
            self.visit(ast.tstmt,newo)
            #get new label for tstmt
            ELABEL = newo.frame.getNewLabel()
            code = self.emit.emitGOTO(ELABEL,newo.frame) #jump to elabel, ignore false stmt
            self.emit.printout(code)
            
            code = self.emit.emitLABEL(FLABEL,newo.frame) # position of flabel
            self.emit.printout(code)
            #visit false stmt
            self.visit(ast.estmt,newo)
            
            code = self.emit.emitLABEL(ELABEL,newo.frame) #position of elabel
            self.emit.printout(code)                
    def visitFor(self, ast, o): 
        o.frame.enterLoop()
        initc,initt = self.visit(ast.init,Access(o.frame,o.sym,False))
        self.emit.printout(initc)
        
        CONLABEL = o.frame.getNewLabel() # jump label if loop
        code = self.emit.emitLABEL(CONLABEL,o.frame) #position of new loop
        self.emit.printout(code)
        
        expc,expt = self.visit(ast.exp,Access(o.frame,o.sym,False)) # visiit condition expression
        self.emit.printout(expc)
        FLABEL = o.frame.getNewLabel() # False label
        code = self.emit.emitIFFALSE(FLABEL,o.frame) # jump to end loop if false
        #else continue loop, visit statement
        self.visit(ast.stmt,o)
        
        #visit update statement
        updc,updt = self.visit(ast.update,Access(o.frame,o.sym,False)) # update
        self.emit.printout(updc)
        code = self.emit.emitGOTO(CONLABEL,o.frame) #go to next loop
        self.emit.printout(code)
        
        code = self.emit.emitLABEL(FLABEL,o.frame) # position for end loop
        self.emit.printout(code)
        o.frame.exitLoop()
    
    def visitWhile(self, ast, o): 
        o.frame.enterLoop()
        ctnLabel = o.frame.getContinueLabel()
        brkLabel = o.frame.getBreakLabel()
        
        code = self.emit.emitLABEL(ctnLabel,o.frame) # position of continue label
        self.emit.printout(code)
        # visit expression
        expc,expt = self.visit(ast.cond,Access(o.frame,o.sym,False))
        self.emit.printout(expc)
        #jump to break label if exp is false
        code =  self.emit.emitIFFALSE(brkLabel,o.frame)
        self.emit.printout(code)
        #else visit stmt
        self.visit(ast.stmt,o)
        code = self.emit.emitGOTO(ctnLabel,o.frame) # jump to continue label
        self.emit.printout(code)
        #position of break label
        code = self.emit.emitLABEL(brkLabel,o.frame)
        self.emit.printout(code)
        o.frame.exitLoop()
    
    def visitDoWhile(self, ast, o): 
        o.frame.enterLoop()
        ctnLabel = o.frame.getContinueLabel()
        brkLabel = o.frame.getBreakLabel()
        
        code = self.emit.emitLABEL(ctnLabel,o.frame)
        self.emit.printout(code)        
        self.visit(ast.stmt.o)
        
        ec,et = self.visit(ast.cond,Access(o.frame,o.sym,False))
        self.emit.printout(ec)
        code = self.emit.emitIFFALSE(brkLabel,o.frame) #jump to next stmt 
        self.emit.printout(code)
        
        code = self.emit.emitGOTO(ctnLabel,o.frame) # jump to next loop
        self.emit.printout(code)
        
        code = self.emit.emitLABEL(brkLabel,o.frame)
        self.emit.printout(code)
        o.frame.exitLoop()
    
    def visitBreak(self, ast, o): 
        self.emit.printout(self.emit.emitGOTO(o.frame.getBreakLabel(), o.frame))
    
    def visitContinue(self, ast, o): 
        self.emit.printout(self.emit.emitGOTO(o.frame.getContinueLabel(), o.frame))
    
    def visitReturn(self, ast, o): 
        if type(o.frame.returnType) is VoidType:
            self.emit.printout(self.emit.emitRETURN(o.frame.returnType,o.frame))
        else:
            ec,et = self.visit(ast.expr,Access(o.frame,o.sym,False,True))
            if type(o.frame.returnType) is FloatType and type(et) is IntegerType:
                ec = ec + self.emit.emitI2F(o.frame)
            self.emit.printout(ec)
            self.emit.printout(self.emit.emitRETURN(o.frame.returnType,o.frame))
                
    def visitCallStmt(self, ast, o):
        ctxt = o
        frame = ctxt.frame
        nenv = ctxt.sym
        sym = next(filter(lambda x: ast.method.name == x.name, nenv), None)
        cname = sym.value.value
        ctype = sym.mtype
        partype = sym.mtype.partype
        in_ = ("", list())
        idx = 0
        for x in ast.args:
            str1, typ1 = self.visit(x, Access(frame, nenv, False, True))
            if type(partype[idx]) is FloatType and type(typ1) is IntegerType:
                str1 = str1 + self.emit.emitI2F(frame)
            in_ = (in_[0] + str1, in_[1].append(typ1))
            idx  = idx + 1
        self.emit.printout(in_[0])
        self.emit.printout(self.emit.emitINVOKESTATIC(
            cname + "/" + ast.method.name, ctype, frame))


################---visit expressions---######################

    def visitBinaryOp(self, ast, o):
        e1c,e1t = self.visit(ast.left,o)
        e2c,e2t = self.visit(ast.right,o)
        
        if type(e1t) == type(e2t):
            rt = e1t
        elif type(e1t) is IntegerType and type(e2t) is FloatType:
            e1c = e1c + self.emit.emitI2F(o.frame)
            rt = e2t
        else:
            e2c = e2c + self.emit.emitI2F(o.frame)
            rt = e1t
            
        if ast.op in ['+','-']:
            op = self.emit.emitADDOP(ast.op,rt,o.frame)
        elif ast.op in ['*']:
            op = self.emit.emitMULOP(ast.op,rt,o.frame)
        elif ast.op in ['/']:
            if type(e1t) is IntegerType and type(e2t) is IntegerType:
                e1c = e1c + self.emit.emitI2F(o.frame)
                e2c = e2c + self.emit.emitI2F(o.frame)
                rt = FloatType()
            op = self.emit.emitMULOP(ast.op,rt,o.frame)
        elif ast.op in ['%']:
            op = self.emit.emitMOD(o.frame)
            rt = IntegerType()
        elif ast.op in ['||']:
            op = self.emit.emitOROP(o.frame)
            rt = BooleanType()
        elif ast.op in ['&&']:
            op = self.emit.emitANDOP(o.frame)
            rt = BooleanType()
        elif ast.op in ['::']:
            op = self.emit.emitOROP(o.frame)
            rt = BooleanType()
        else:
            op = self.emit.emitREOP(ast.op,rt,o.frame)
            rt = BooleanType()
        return e1c + e2c + op,rt
    
    def visitUnaryOp(self, ast, o): 
        ctxt = o
        ec, et = self.visit(ast.val, ctxt)
        if ast.op == '-': return ec + self.emit.emitNEGOP(et, ctxt.frame), et
        if ast.op == '!': return ec + self.emit.emitNOT(et, ctxt.frame), et
            
    def visitFuncCall(self,ast,o): pass
    
    def visitId(self,ast,o):
        ctxt = o
        sym = list(filter(lambda x: x.name == ast.name,o.sym))[0]
        mtype = sym.mtype if type(sym.mtype) is not ArrayType else sym.mtype.typ 
        if type(sym.value) is Index:
            if ctxt.isLeft and type(sym.mtype) is not ArrayType:
                code = self.emit.emitWRITEVAR(sym.name,mtype,sym.value.value,o.frame)
            else:
                code = self.emit.emitREADVAR(sym.name,mtype,sym.value.value,o.frame)
        else: 
            if ctxt.isLeft and type(sym.mtype) is not ArrayType:
                code = self.emit.emitPUTSTATIC(sym.value.value + "." + sym.name,mtype,o.frame  )
            else:
                code = self.emit.emitGETSTATIC(sym.value.value + "." + sym.name,mtype,o.frame)
            
        return code,sym.mtype       
    
    def visitArrayCell(self,ast,o): 
        ctxt = o
        arrc,arrt = self.visit(ast.name,Access(ctxt.frame,ctxt.sym,True,True))
        in_ = ""
        for x in ast.cell:
            ec,et = self.visit(x,Access(ctxt.frame,ctxt.sym,False,True))
            in_ = in_ + ec
        if ctxt.isLeft:
            return  [arrc + in_, self.emit.emitALOAD(arrt.typ,ctxt.frame)],arrt.typ
        else:
            return arrc + in_ + self.emit.emitALOAD(arrt.typ,ctxt.frame),arrt.typ
    def visitIntegerLit(self, ast, o):
        return self.emit.emitPUSHICONST(ast.value, o.frame), IntegerType()
    
    def visitFloatLit(self, ast, o):
        return self.emit.emitPUSHFCONST(str(ast.value), o.frame), FloatType()

    def visitBooleanLit(self, ast, o):
        return self.emit.emitPUSHICONST(str(ast.value).lower(), o.frame), BooleanType()

    def visitStringLit(self, ast, o):
        return self.emit.emitPUSHCONST(ast.value, StringType(), o.frame), StringType()