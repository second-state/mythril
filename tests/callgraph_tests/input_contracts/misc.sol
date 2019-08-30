contract Misc {
  function f1() public {
    f2();
    f5();
  }
  function f2() public {
    f3();
    f7();
  }
  function f3() public {
    f1();
  }
  function f4() public {
    f1();
  }
  function f5() public {
    f6();
  }
  function f6() public {
  }
  function f7() public {
    f2();
  }
  function f8() public {
    f9();
    f10();
  }
  function f9() public {
    f11();
  }
  function f10() public {
    f12();
    f13();
  }
  function f11() public {
    f12();
  }
  function f12() public {
    f11();
  }
  function f13() public {
  }
}
