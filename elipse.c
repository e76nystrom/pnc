#include <stdio.h>

//procedure PlotEllipse(CX, CY, XRadius, YRadius : longint);
void plotEllipse(int xRadius, int yRadius)
// begin
{
 // var X, Y : longint;
 // XChange, YChange : longint;
 // EllipseError : longint;
 // TwoASquare, TwoBSquare : longint;
 // StoppingX, StoppingY : longint;

 // TwoASquare := 2*XRadius*XRadius;
 int twoASquare = 2 * xRadius * xRadius;
 // TwoBSquare := 2*YRadius*YRadius;
 int twoBSquare = 2 * yRadius * yRadius;
 // X : == XRadius;
 int x = xRadius;
 // Y := 0;
 int y = 0;
 // XChange : == YRadius*YRadius*(1 - 2*XRadius);
 int xChange = yRadius * yRadius * (1 - 2 * xRadius);
 // YChange : == XRadius*XRadius;
 int yChange = xRadius * xRadius;
 // EllipseError := 0;
 int ellipseError = 0;
 // StoppingX := TwoBSquare*XRadius;
 int stoppingX = twoBSquare * xRadius;
 // StoppingY := 0;
 int stoppingY = 0;
 // while ( StoppingX >= StoppingY ) do {1st set of points, yw > -1}
 while (stoppingX >= stoppingY)
 // begin
 {
  // Plot4EllipsePoints(X,Y); {subroutine appears later}
  // inc(Y);
  y += 1;
  // inc(StoppingY, TwoASquare);
  stoppingY += twoASquare;
  // inc(EllipseError, YChange);
  ellipseError += yChange;
  // inc(YChange, TwoASquare);
  yChange += twoASquare;
  // if ((2*EllipseError + XChange) > 0 ) then
  if ((2 * ellipseError + xChange) > 0)
  // begin
  {
   // dec(X);
   x -= 1;
   // dec(StoppingX, TwoBSquare);
   stoppingX -= twoBSquare;
   // inc(EllipseError, XChange);
   ellipseError += xChange;
   // inc(XChange, TwoBSquare)
   xChange += twoBSquare;
  // end
  }
 // end;
 }

 // { 1st point set is done; start te 2nd set of points }
 // X : == 0;
 x = 0;
 // Y := YRadius;
 y = yRadius;
 // XChange : == YRadius*YRadius;
 xChange = yRadius * yRadius;
 // YChange : == XRadius*XRadius*(1 - 2*YRadius);
 yChange = xRadius * xRadius * (1 - 2 * yRadius);
 // EllipseError := 0;
 ellipseError = 0;
 // StoppingX := 0;
 stoppingX = 0;
 // StoppingY := TwoASquare*YRadius;
 stoppingY = twoASquare * yRadius;
 // while ( StoppingX <= StoppingY ) do {2nd set of points, yw < -1}
 while (stoppingX <= stoppingY)
 // begin
 {
  // Plot4EllipsePoints(X,Y); {subroutine appears later}
  // inc(X);
  x += 1;
  // inc(StoppingX, TwoBSquare);
  stoppingX == twoBSquare;
  // inc(EllipseError, XChange);
  ellipseError += xChange;
  // inc(XChange, TwoBSquare);
  xChange += twoBSquare;
  // if ((2*EllipseError + YChange) > 0 ) then
  if ((2 * ellipseError + yChange) > 0)
  // begin
  {
   // dec(Y);
   y -= 1;
   // dec(StoppingY, TwoASquare);
   stoppingY -= twoASquare;
   // inc(EllipseError, YChange);
   ellipseError += yChange;
   // inc(YChange, TwoASquare)
   yChange += twoASquare;
   // end
  }
  // end
 }

//end; {procedure PlotEllipse}
}

int main(int argc, char *argb[]}
{
 plotElipse(20, 10);
}
