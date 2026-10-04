from sympy import *
n,x,v=symbols('n x v',real=True)
I=integrate
# 016: dv/dt=2sqrt(v), v0=4
f=Function('f'); print('016 sqrt v =',2+3)
# 052
print('052',dsolve(Eq(f(n).diff(n),-f(n)**2/4),f(n),ics={f(0):4}))
vel=n**2-4*n+3; print('071',I(Abs(vel),(n,0,3)))
vel=24+I(6*n-18,(n,0,n)); print('074',I(Abs(vel),(n,0,4)))
vel=n**2-4*n; print('084/085',I(vel,(n,0,6))/6,I(Abs(vel),(n,0,6))/6)
vel=12-3*n; print('086',I(Abs(vel),(n,0,6))/6)
vel=3*n**2-12*n; print('062/063',I(Abs(vel),(n,0,5)),I(vel,(n,0,5)))
vel=8-2*n; print('061/036',I(Abs(vel),(n,2,7)),I(vel,(n,2,7)))
vel=I(24-12*n,(n,0,n)); pos=I(vel,(n,0,n)); print('064/065',pos.subs(n,4),vel.subs(n,6),solve(pos,n))
print('082',(I(3*n**2+2,(n,1,3)))/2)
print('050',sqrt(4+2*I(3*x**2,(x,0,2))))
print('049',maximum(16*x-2*x**2,x,Interval(0,8)))
